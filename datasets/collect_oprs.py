"""Collect Fair Haven OPRS Property Record Card data — batch-based, VPN-swap friendly.

Replaces ad-hoc OPRS scrapers. Designed for the operational pattern:
    1. Connect to VPN exit IP A
    2. uv run python datasets/collect_oprs.py --batch 500 --rate 2.0 [--mode comprehensive]
    3. Script processes up to N requests, exits cleanly with status
    4. Connect to VPN exit IP B
    5. Run again — resumes from cache, processes next N
    6. Repeat until --status reports complete

Per-parcel processing:
    For each parcel (sorted ascending PAMS_PIN order):
      1. Fetch m4.html (the full PRC summary with hist=1) if not cached.
         m4 always fetched regardless of mode — it's the index of the parcel.
      2. If --mode comprehensive: parse m4.html for sale serial numbers (ssi
         values), then fetch one sr.html per ssi (sr_{ssi}.html in the cache).
         Each sale gets its own file. Captures grantor/grantee, REMARKS,
         family-sale flag, assessor sales-ratio per individual sale.

    Each parcel completes fully before moving to the next, so partial caches
    always represent contiguous fully-resolved parcels (handy for inspecting
    progress mid-run).

Key properties:
    - Idempotent: never re-fetches a component already cached. Re-running
      with --mode comprehensive after a --mode basic run only fetches the
      missing sr_{ssi}.html files.
    - Atomic writes: components write to .tmp sibling, rename on success.
      Interrupted writes leave NO incomplete files.
    - Content validation: rejects empty-form responses (200 OK + ~13 KB
      blank PRC template) — confirms the requested block AND lot integers
      are actually rendered in the page body.
    - Order: parcels in sorted PAMS_PIN order; ssis within a parcel in
      ascending numeric order. Deterministic, resumable.
    - Auto-abort: rolling error rate over a sliding window of recent
      requests. Trips with a clear "switch VPN" message if exceeded.

Usage:
    uv run python datasets/collect_oprs.py --status
    uv run python datasets/collect_oprs.py --batch 500 --rate 2.0
    uv run python datasets/collect_oprs.py --mode comprehensive --batch 500
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pdfplumber
import requests


PARCELS_DEFAULT = Path("data/processed/parcels.parquet")
OUTPUT_DEFAULT = Path("data/raw/oprs_prc")
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
REFERER = "https://oprs.co.monmouth.nj.us/"

M4_BASE = "https://tax1.co.monmouth.nj.us/cgi-bin/m4.cgi"
SR_BASE = "https://tax1.co.monmouth.nj.us/cgi-bin/sr.cgi"
PRC_BASE = "https://tax1.co.monmouth.nj.us/cgi-bin/prc.cgi"
CH75_BASE = "https://tax1.co.monmouth.nj.us/cgi-bin/ch75.cgi"
TAXLIST_BASE = "https://tax1.co.monmouth.nj.us/cgi-bin/taxlist.cgi"
TAX1_HOST = "https://tax1.co.monmouth.nj.us"

DISTRICT = "1314"  # Fair Haven NJGIN code

# Operator updates this annually when the next year's tax list becomes available.
CURRENT_YEAR = 2026

COMPONENT_M4 = "m4.html"
COMPONENT_PRC = "prc.pdf"
COMPONENT_CH75 = "ch75.pdf"


# ----------------------------------------------------------------------------
# Config / state
# ----------------------------------------------------------------------------

@dataclass
class Config:
    parcels_path: Path
    output_root: Path
    mode: str               # "basic" or "comprehensive"
    batch_size: int
    rate_per_second: float
    jitter_pct: float
    max_error_rate: float
    error_window: int
    error_min_samples: int
    max_retries: int


@dataclass
class RunState:
    requests_done: int = 0
    cache_hits: int = 0
    fetched_ok: int = 0
    fetched_no_sale: int = 0
    fetched_fail: int = 0
    parcels_completed: int = 0
    aborted: bool = False
    abort_reason: str | None = None
    recent_errors: deque = field(default_factory=lambda: deque(maxlen=200))


# ----------------------------------------------------------------------------
# PAMS_PIN ↔ OPRS URL encoding
# ----------------------------------------------------------------------------

def _split_block_lot(value: str) -> tuple[str, str]:
    """'77.01' → ('77', '01'); '15' → ('15', '')."""
    if "." in value:
        a, b = value.split(".", 1)
        return a, b
    return value, ""


def encode_l02(block: str, lot: str, qualifier: str = "") -> str:
    """Encode (block, lot, qualifier) → 28-char OPRS l02 URL parameter.

    Format: DDDD BBBBB SSSS LLLLL XXXX QQQQQ M
        district(4) + block_base(5) + block_suffix(4) + lot_base(5) +
        lot_suffix(4) + qualifier(5) + 'M'  =  28 chars

    Block/lot bases zero-pad-LEFT; suffixes RIGHT-justify with underscore
    fill. Verified against live samples:
        '131400003____00033_________M'  (block=3 lot=33, no suffixes/qual)
        '131400077____00080__02_____M'  (block=77 lot=80.02)
    """
    block_base, block_suffix = _split_block_lot(block)
    lot_base, lot_suffix = _split_block_lot(lot)
    parts = [
        DISTRICT,
        block_base.zfill(5),
        (block_suffix or "").rjust(4, "_"),
        lot_base.zfill(5),
        (lot_suffix or "").rjust(4, "_"),
        (qualifier or "").ljust(5, "_"),
        "M",
    ]
    return "".join(parts)


def parse_pams_pin(pin: str) -> tuple[str, str, str]:
    """'1314_BLOCK_LOT' or '1314_BLOCK_LOT_QUAL' → (block, lot, qualifier)."""
    parts = pin.split("_")
    if len(parts) == 3:
        return parts[1], parts[2], ""
    if len(parts) == 4:
        return parts[1], parts[2], parts[3]
    raise ValueError(f"unrecognized pams_pin: {pin!r}")


# ----------------------------------------------------------------------------
# Cache layout
#
# Each parcel gets its own subdirectory under output_root, e.g.
#     data/raw/oprs_prc/1314_3_33/
#         m4.html              — the m4.cgi summary
#         sr_1331.html         — sr.cgi for sale serial 1331
#         sr_1549.html         — etc.
#         sr_1549.html.no_sale — marker for ssis that legitimately return empty
#
# Markers exist so we don't refetch known-empty results across batches.
# ----------------------------------------------------------------------------

def parcel_dir(output_root: Path, pams_pin: str) -> Path:
    return output_root / pams_pin


def is_cached(output_root: Path, pams_pin: str, component: str) -> bool:
    """A component is satisfied if either the real file (>200 bytes) or a
    .no_sale marker exists."""
    base = parcel_dir(output_root, pams_pin) / component
    if base.exists() and base.stat().st_size > 200:
        return True
    marker = base.with_suffix(base.suffix + ".no_sale")
    return marker.exists()


def sr_component_name(ssi: str) -> str:
    return f"sr_{ssi}.html"


def taxlist_component_name(year: int) -> str:
    return f"taxlist_{year}.pdf"


_TAXLIST_YEAR_RE = re.compile(r"^taxlist_(\d{4})\.pdf$")


# ----------------------------------------------------------------------------
# Parsing m4 to discover ssi values for sales
# ----------------------------------------------------------------------------

_SSI_RE = re.compile(r'sr\.cgi\?[^"\']*?ssi=(\d+)[^"\']*?block=(\d+)[^"\']*?lot=(\d+)')

# D-27: cgi response embeds an href= or src= ref to a session-bound tmp/<random>.pdf
# URL. Real OPRS responses use unquoted attributes (frame src=../tmp/x.pdf, body
# onload=window.location.href='../tmp/x.pdf', plain <a href=../tmp/x.pdf>) so quotes
# are optional and we accept both href and src.
_PDF_HREF_RE = re.compile(
    r'''(?:href|src)\s*=\s*["']?([^"'>\s]*tmp/[^"'>\s]+\.pdf)''',
    re.I,
)


def extract_ssis_from_m4(m4_html: str) -> list[str]:
    """Pull the list of sale-detail serial numbers from an m4.html page.

    Each historical sale has a 'More Info' link of the form
        sr.cgi?&district=1314&ms_user=&ssi=NNNN&block=B&lot=L&qual=...
    Returns ssi values in document order (which matches sale-history order
    in the rendered page) and de-duplicates while preserving order.
    """
    seen: list[str] = []
    for m in _SSI_RE.finditer(m4_html):
        ssi = m.group(1)
        if ssi not in seen:
            seen.append(ssi)
    return seen


# ----------------------------------------------------------------------------
# HTTP fetch + atomic write + content validation
# ----------------------------------------------------------------------------

def _new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": REFERER,
    })
    return s


def _fetch(session: requests.Session, url: str, timeout: int = 30) -> tuple[int, bytes | None]:
    try:
        r = session.get(url, timeout=timeout)
        return r.status_code, r.content
    except requests.RequestException:
        return 0, None


def _write_atomic(path: Path, data: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp, "wb") as f:
            f.write(data)
        tmp.replace(path)
        return True
    except OSError:
        tmp.unlink(missing_ok=True)
        return False


def _is_empty_sr_template(flat: str) -> bool:
    """sr.cgi returns a structurally identical 'no detail on record' page
    when the requested ssi has no associated sale. Detect via the date
    placeholder ' // // ' that only appears in the empty form."""
    return " // // " in flat


def _validate(component: str, body: bytes, block: str, lot: str) -> tuple[bool, str]:
    """Confirm the response actually contains the requested parcel's data.
    Returns (ok, status_tag). Special status_tag='no_sale' for empty sr."""
    if not body or len(body) < 500:
        return False, f"too_small:{len(body) if body else 0}"
    # D-30: PDF components must have a %PDF marker. Header strip (D-28) is
    # applied upstream in _fetch_pdf_two_step for prc.pdf, so by the time we
    # see the body here it should start with b"%PDF" if valid.
    if component.endswith(".pdf"):
        if not body.startswith(b"%PDF"):
            return False, "no_pdf_marker"
        return True, "ok"
    text = body.decode("latin-1", errors="replace")
    flat = re.sub(r"<[^>]+>", " ", text)
    flat = re.sub(r"&nbsp;|&amp;", " ", flat)
    flat = re.sub(r"\s+", " ", flat)
    block_int = block.lstrip("0").split(".")[0] or "0"
    lot_int = lot.lstrip("0").split(".")[0] or "0"
    block_match = re.search(rf"\bBlock:?\s+{re.escape(block_int)}(?:\.\d+)?\b", flat, re.IGNORECASE)
    lot_match = re.search(rf"\bLot:?\s+{re.escape(lot_int)}(?:\.\d+)?\b", flat, re.IGNORECASE)
    if not block_match or not lot_match:
        if component.startswith("sr_") and _is_empty_sr_template(flat):
            return False, "no_sale"
        if not block_match:
            return False, f"empty_form:block_missing:{block_int}"
        return False, f"empty_form:lot_missing:{lot_int}"
    return True, "ok"


def _build_url(component: str, block: str, lot: str, qualifier: str, ssi: str | None) -> str:
    if component == COMPONENT_M4:
        l02 = encode_l02(block, lot, qualifier)
        return f"{M4_BASE}?district={DISTRICT}&l02={l02}&hist=1"
    if component.startswith("sr_") and ssi:
        return f"{SR_BASE}?&district={DISTRICT}&ms_user=&ssi={ssi}&block={block}&lot={lot}&qual={qualifier}"
    # PDF endpoints use h00/h01/h02/ccdd parameters per docs/specs/oprs_samples/README.md.
    # Verified live: l02-style params return generic stubs (prc) or "not found" (ch75/taxlist).
    if component == COMPONENT_PRC:
        return (
            f"{PRC_BASE}?h00={block}&h01={lot}&h02={qualifier}&ccdd={DISTRICT}"
        )
    if component == COMPONENT_CH75:
        return (
            f"{CH75_BASE}?h00={block}&h01={lot}&h02={qualifier}&i24=2&ccdd={DISTRICT}"
        )
    if component.startswith("taxlist_") and component.endswith(".pdf"):
        m = _TAXLIST_YEAR_RE.match(component)
        if not m:
            raise ValueError(f"can't parse year from taxlist component {component!r}")
        year = m.group(1)
        return (
            f"{TAXLIST_BASE}?h00={block}&h01={lot}&h02={qualifier}"
            f"&year={year}&ccdd={DISTRICT}"
        )
    raise ValueError(f"can't build URL for component {component!r} ssi={ssi!r}")


def _fetch_pdf_two_step(
    session: requests.Session, cgi_url: str, component: str, timeout: int = 30
) -> tuple[int, bytes | None, int]:
    """D-27: Two-request session-bound PDF fetch.

    1. GET cgi_url → HTML containing href to tmp/<random>.pdf
    2. GET the resolved tmp PDF URL on the same session

    For COMPONENT_PRC only (D-28), slice the body from the b"%PDF" marker —
    upstream Apache prepends a literal HTTP envelope despite a 200 OK status.

    Returns (status_code, body, requests_made).
        - cgi step fails → (status, None, 1)
        - href not found → (200, None, 1)
        - second GET fails → (status, None, 2)
        - success → (200, body, 2)
    """
    try:
        r1 = session.get(cgi_url, timeout=timeout)
    except requests.RequestException:
        return 0, None, 1
    if r1.status_code != 200 or not r1.content:
        return r1.status_code, None, 1
    html = r1.content.decode("latin-1", errors="replace")
    m = _PDF_HREF_RE.search(html)
    if not m:
        return 200, None, 1
    href = m.group(1)
    if href.startswith("http://") or href.startswith("https://"):
        pdf_url = href
    elif href.startswith("/"):
        pdf_url = TAX1_HOST + href
    else:
        pdf_url = TAX1_HOST + "/" + href
    try:
        r2 = session.get(pdf_url, timeout=timeout)
    except requests.RequestException:
        return 0, None, 2
    if r2.status_code != 200 or not r2.content:
        return r2.status_code, None, 2
    body = r2.content
    if component == COMPONENT_PRC:
        # D-28: strip prepended HTTP envelope by slicing from %PDF marker.
        if body.find(b"%PDF") > 0:
            body = body[body.find(b"%PDF"):]
    return 200, body, 2


def _pdfplumber_page1_ok(path: Path) -> bool:
    """D-30: a valid PDF must yield non-empty extractable text.

    Try pdfplumber first; fall back to pdfminer.six (pdfplumber's underlying
    engine) for PDFs whose MediaBox is missing — pdfplumber's Page __init__
    raises on that, but pdfminer handles it gracefully. ch75.cgi PDFs are
    structurally valid but trip the pdfplumber MediaBox check.
    """
    try:
        with pdfplumber.open(str(path)) as pdf:
            if not pdf.pages:
                return False
            text = pdf.pages[0].extract_text() or ""
            if text.strip():
                return True
    except Exception:
        pass
    # Fallback for MediaBox-missing or otherwise pdfplumber-hostile PDFs.
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(str(path), maxpages=1) or ""
        return bool(text.strip())
    except Exception:
        return False


def fetch_component(
    session: requests.Session,
    pams_pin: str,
    component: str,
    output_root: Path,
    max_retries: int,
    ssi: str | None = None,
) -> tuple[bool, str, int]:
    """Fetch one component, atomic-write to cache.

    Returns (ok, status_string, requests_made).
        - cached → (True, "cached", 0)
        - HTML success → (True, "ok", 1)
        - PDF success → (True, "ok", 2)
        - failure → (False, status, requests_made_so_far summed across retries)
    """
    if is_cached(output_root, pams_pin, component):
        return True, "cached", 0
    block, lot, qualifier = parse_pams_pin(pams_pin)
    url = _build_url(component, block, lot, qualifier, ssi)
    is_pdf = component.endswith(".pdf")

    last_status = "no_attempt"
    total_requests = 0
    for attempt in range(max_retries):
        if is_pdf:
            status_code, body, made = _fetch_pdf_two_step(session, url, component)
            total_requests += made
        else:
            status_code, body = _fetch(session, url)
            total_requests += 1
        if status_code == 0:
            last_status = "network_err"
            time.sleep(1.0 + attempt)
            continue
        if status_code != 200:
            last_status = f"http_{status_code}"
            time.sleep(1.0 + attempt)
            continue
        if body is None:
            last_status = "no_pdf_href" if is_pdf else "empty_body"
            time.sleep(0.5)
            continue
        valid, vstatus = _validate(component, body, block, lot)
        if vstatus == "no_sale":
            marker = parcel_dir(output_root, pams_pin) / (component + ".no_sale")
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_bytes(b"no_detail_on_record\n")
            return True, "no_sale", total_requests
        if not valid:
            last_status = vstatus
            time.sleep(0.5)
            continue
        out = parcel_dir(output_root, pams_pin) / component
        if not _write_atomic(out, body):
            last_status = f"write_failed:{len(body) if body else 0}"
            time.sleep(0.5)
            continue
        # D-30: post-write pdfplumber sanity check for PDF components.
        if is_pdf:
            if not _pdfplumber_page1_ok(out):
                # unlink and retry
                try:
                    out.unlink()
                except OSError:
                    pass
                last_status = "pdfplumber_failed"
                time.sleep(0.5)
                continue
        return True, "ok", total_requests

    return False, last_status, total_requests


# ----------------------------------------------------------------------------
# Workload
# ----------------------------------------------------------------------------

def load_parcel_ids(parcels_path: Path) -> list[str]:
    suffix = parcels_path.suffix.lower()
    if suffix == ".parquet":
        try:
            df = gpd.read_parquet(parcels_path)
        except Exception:
            import pandas as pd
            df = pd.read_parquet(parcels_path)
        col = "pams_pin" if "pams_pin" in df.columns else "PAMS_PIN"
        ids = df[col].dropna().astype(str).tolist()
    elif suffix == ".csv":
        import pandas as pd
        df = pd.read_csv(parcels_path, dtype=str)
        col = "pams_pin" if "pams_pin" in df.columns else "PAMS_PIN"
        ids = df[col].dropna().astype(str).tolist()
    elif suffix == ".json":
        with open(parcels_path) as f:
            ids = json.load(f)
        if isinstance(ids, dict):
            ids = ids.get("parcels") or list(ids.keys())
    else:
        raise ValueError(f"unsupported parcel input format: {suffix}")
    return sorted(set(ids))


def parcel_needed_components(
    output_root: Path, pams_pin: str, mode: str
) -> list[tuple[str, str | None]]:
    """Return list of (component, ssi) tuples this parcel still needs.

    For comprehensive mode, sr components are only listed if m4 is already
    cached (since we need m4 to discover ssi values). If m4 isn't cached,
    only m4 is listed and the next batch will discover ssis after fetching it.
    """
    needed: list[tuple[str, str | None]] = []
    if not is_cached(output_root, pams_pin, COMPONENT_M4):
        needed.append((COMPONENT_M4, None))
        if mode == "basic":
            return needed
        # We can't enumerate ssis until m4 is on disk; the inline run loop
        # will append sr work right after the m4 fetch succeeds.
        return needed

    if mode != "comprehensive":
        return needed

    # m4 is cached — read it and enumerate ssis
    m4_path = parcel_dir(output_root, pams_pin) / COMPONENT_M4
    try:
        text = m4_path.read_text(errors="replace")
    except OSError:
        return needed
    for ssi in extract_ssis_from_m4(text):
        comp = sr_component_name(ssi)
        if not is_cached(output_root, pams_pin, comp):
            needed.append((comp, ssi))

    # PDF components — comprehensive mode adds prc.pdf, ch75.pdf, taxlist_<year>.pdf
    # alongside sr discovery (D-29: each component independently cached).
    for pdf_comp in (
        COMPONENT_PRC,
        COMPONENT_CH75,
        taxlist_component_name(CURRENT_YEAR),
    ):
        if not is_cached(output_root, pams_pin, pdf_comp):
            needed.append((pdf_comp, None))
    return needed


# ----------------------------------------------------------------------------
# Run loop with rolling error-rate abort
# ----------------------------------------------------------------------------

def _sleep_pacing(rate: float, jitter_pct: float) -> None:
    base = 1.0 / rate if rate > 0 else 0.0
    jitter = base * jitter_pct * (random.random() * 2 - 1)
    delay = max(0.05, base + jitter)
    time.sleep(delay)


def _check_abort(state: RunState, cfg: Config) -> tuple[bool, str | None]:
    if cfg.error_window <= 0 or cfg.max_error_rate <= 0:
        return False, None
    samples = list(state.recent_errors)
    if len(samples) < cfg.error_min_samples:
        return False, None
    window = samples[-cfg.error_window:]
    err = sum(1 for ok in window if not ok)
    rate = err / len(window)
    if rate > cfg.max_error_rate:
        return True, (
            f"error rate {rate:.0%} ({err}/{len(window)}) exceeds threshold "
            f"{cfg.max_error_rate:.0%} — likely VPN/IP blocked. Switch and re-run."
        )
    return False, None


def run_batch(cfg: Config) -> RunState:
    state = RunState()
    cfg.output_root.mkdir(parents=True, exist_ok=True)
    log_path = cfg.output_root / "_collect.log"

    def log(msg: str) -> None:
        line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
        print(line, flush=True)
        with open(log_path, "a") as f:
            f.write(line + "\n")

    parcel_ids = load_parcel_ids(cfg.parcels_path)
    log(
        f"start mode={cfg.mode} batch={cfg.batch_size} rate={cfg.rate_per_second}/s "
        f"jitter={cfg.jitter_pct} parcels={len(parcel_ids)} output={cfg.output_root}"
    )

    session = _new_session()

    for pin in parcel_ids:
        if state.requests_done >= cfg.batch_size or state.aborted:
            break

        # Build per-parcel work queue dynamically (m4 first; sr items
        # discovered after m4 is cached).
        work = deque(parcel_needed_components(cfg.output_root, pin, cfg.mode))
        if not work:
            continue  # already fully cached for this mode

        while work and state.requests_done < cfg.batch_size:
            component, ssi = work.popleft()
            ok, status, requests_made = fetch_component(
                session, pin, component, cfg.output_root, cfg.max_retries, ssi=ssi
            )
            # PDF components consume two requests per attempt (D-27); HTML
            # components consume one. Cached returns 0.
            state.requests_done += max(requests_made, 1) if status != "cached" else 0
            state.recent_errors.append(ok)
            if status == "cached":
                state.cache_hits += 1
            elif status == "no_sale":
                state.fetched_no_sale += 1
            elif ok:
                state.fetched_ok += 1
            else:
                state.fetched_fail += 1

            label = f"{pin}/{component}"
            if state.requests_done % 25 == 0:
                log(
                    f"  [{state.requests_done}/{cfg.batch_size}] {label} "
                    f"status={status} ok={state.fetched_ok} no_sale={state.fetched_no_sale} "
                    f"fail={state.fetched_fail}"
                )
            else:
                log(f"  {label} status={status}")

            # If we just successfully fetched the m4 component for a
            # comprehensive run, enumerate its ssis and add them to the
            # work queue for THIS parcel before moving on.
            if (
                component == COMPONENT_M4
                and ok
                and status != "cached"
                and cfg.mode == "comprehensive"
            ):
                m4_path = parcel_dir(cfg.output_root, pin) / COMPONENT_M4
                try:
                    text = m4_path.read_text(errors="replace")
                except OSError:
                    text = ""
                discovered = extract_ssis_from_m4(text)
                for ssi_v in discovered:
                    sr_comp = sr_component_name(ssi_v)
                    if not is_cached(cfg.output_root, pin, sr_comp):
                        work.append((sr_comp, ssi_v))
                log(f"    {pin}: discovered {len(discovered)} ssi(s) from m4")

            should_abort, reason = _check_abort(state, cfg)
            if should_abort:
                state.aborted = True
                state.abort_reason = reason
                log(f"ABORT: {reason}")
                break

            _sleep_pacing(cfg.rate_per_second, cfg.jitter_pct)

        if not work:
            state.parcels_completed += 1

    log(
        f"batch end: requests={state.requests_done} ok={state.fetched_ok} "
        f"no_sale={state.fetched_no_sale} fail={state.fetched_fail} "
        f"parcels_completed={state.parcels_completed} aborted={state.aborted}"
    )
    return state


# ----------------------------------------------------------------------------
# Status reporting
# ----------------------------------------------------------------------------

def report_status(cfg: Config) -> None:
    parcel_ids = load_parcel_ids(cfg.parcels_path)
    total = len(parcel_ids)
    m4_cached = 0
    parcels_complete = 0
    sr_cached = 0
    sr_no_sale = 0
    sr_required = 0
    sr_pending = 0
    prc_cached = 0
    prc_pending = 0
    ch75_cached = 0
    ch75_pending = 0
    taxlist_cached = 0
    taxlist_pending = 0
    taxlist_comp = taxlist_component_name(CURRENT_YEAR)

    for pin in parcel_ids:
        m4_present = is_cached(cfg.output_root, pin, COMPONENT_M4)
        if m4_present:
            m4_cached += 1
        if cfg.mode == "basic":
            if m4_present:
                parcels_complete += 1
            continue
        # Comprehensive — enumerate ssis from m4 (if cached)
        if not m4_present:
            continue
        m4_path = parcel_dir(cfg.output_root, pin) / COMPONENT_M4
        try:
            text = m4_path.read_text(errors="replace")
        except OSError:
            text = ""
        ssis = extract_ssis_from_m4(text)
        sr_required += len(ssis)
        all_sr_done = True
        for ssi in ssis:
            comp = sr_component_name(ssi)
            real = (parcel_dir(cfg.output_root, pin) / comp).exists()
            marker = (parcel_dir(cfg.output_root, pin) / (comp + ".no_sale")).exists()
            if real:
                sr_cached += 1
            elif marker:
                sr_no_sale += 1
            else:
                all_sr_done = False
                sr_pending += 1
        # PDF components — independent of sr discovery
        all_pdfs_done = True
        for pdf_comp, c_count, p_count in (
            (COMPONENT_PRC, "prc", "prc_p"),
            (COMPONENT_CH75, "ch75", "ch75_p"),
            (taxlist_comp, "taxlist", "taxlist_p"),
        ):
            if is_cached(cfg.output_root, pin, pdf_comp):
                if pdf_comp == COMPONENT_PRC:
                    prc_cached += 1
                elif pdf_comp == COMPONENT_CH75:
                    ch75_cached += 1
                else:
                    taxlist_cached += 1
            else:
                all_pdfs_done = False
                if pdf_comp == COMPONENT_PRC:
                    prc_pending += 1
                elif pdf_comp == COMPONENT_CH75:
                    ch75_pending += 1
                else:
                    taxlist_pending += 1
        if all_sr_done and all_pdfs_done:
            parcels_complete += 1

    print(f"OPRS cache status — mode={cfg.mode} output={cfg.output_root}")
    print(f"  parcels total:            {total}")
    print(f"  m4.html cached:           {m4_cached} ({100*m4_cached/total:.1f}%)")
    print(f"  parcels fully complete:   {parcels_complete} ({100*parcels_complete/total:.1f}%)")
    if cfg.mode == "comprehensive":
        print(f"  sr (real):                {sr_cached}")
        print(f"  sr (no_sale markers):     {sr_no_sale}")
        print(f"  sr pending:               {sr_pending}")
        print(f"  sr total expected (so far from cached m4s): {sr_required}")
        print(f"  prc.pdf cached:           {prc_cached}  pending: {prc_pending}")
        print(f"  ch75.pdf cached:          {ch75_cached}  pending: {ch75_pending}")
        print(f"  {taxlist_comp} cached:   {taxlist_cached}  pending: {taxlist_pending}")
        # Estimate remaining work — sr_pending plus m4-not-yet-cached parcels'
        # average ssi count (~3-4 per Fair Haven parcel). PDFs cost 2 requests
        # each (D-27).
        m4_pending = total - m4_cached
        pdf_pending = prc_pending + ch75_pending + taxlist_pending
        est_remaining = sr_pending + m4_pending * 3 + pdf_pending * 2
        print(f"  rough remaining requests: ~{m4_pending + est_remaining}")
        print(f"  estimated batches at batch={cfg.batch_size}: ~{-(-est_remaining // cfg.batch_size)}")


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(
        description="Collect Fair Haven OPRS Property Record Card data "
        "(per-parcel, batch-based, VPN-swap friendly, idempotent, atomic).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--parcels-from", type=Path, default=PARCELS_DEFAULT,
                   help="Parquet/CSV/JSON with PAMS_PINs (column 'pams_pin')")
    p.add_argument("--output-dir", type=Path, default=OUTPUT_DEFAULT,
                   help="Cache root. Each parcel gets a subdir.")
    p.add_argument("--mode", choices=["basic", "comprehensive"], default="basic",
                   help="basic = m4 only; comprehensive = m4 + sr per discovered sale")
    p.add_argument("--batch", dest="batch_size", type=int, default=500,
                   help="Max requests per invocation")
    p.add_argument("--rate", dest="rate_per_second", type=float, default=2.0,
                   help="Target requests per second")
    p.add_argument("--jitter-pct", type=float, default=0.15,
                   help="Random jitter as fraction of base interval")
    p.add_argument("--max-error-rate", type=float, default=0.10,
                   help="Abort if rolling error rate exceeds this fraction")
    p.add_argument("--error-window", type=int, default=50,
                   help="Sliding window size for error-rate calc")
    p.add_argument("--error-min-samples", type=int, default=20,
                   help="Don't trip abort until at least this many requests")
    p.add_argument("--max-retries", type=int, default=3,
                   help="Retries per component before giving up")
    p.add_argument("--status", action="store_true",
                   help="Print cache status and exit")
    args = p.parse_args()

    cfg = Config(
        parcels_path=args.parcels_from,
        output_root=args.output_dir,
        mode=args.mode,
        batch_size=args.batch_size,
        rate_per_second=args.rate_per_second,
        jitter_pct=args.jitter_pct,
        max_error_rate=args.max_error_rate,
        error_window=args.error_window,
        error_min_samples=args.error_min_samples,
        max_retries=args.max_retries,
    )

    if args.status:
        report_status(cfg)
        return 0

    state = run_batch(cfg)
    if state.aborted:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
