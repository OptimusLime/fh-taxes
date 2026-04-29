"""Collect Fair Haven OPRS Property Record Card data — batch-based, VPN-swap friendly.

Replaces ad-hoc OPRS scrapers. Designed for the operational pattern:
    1. Connect to VPN exit IP A
    2. uv run python datasets/collect_oprs.py --batch 500 --rate 2.0
    3. Script processes 500 requests, exits cleanly with status
    4. Connect to VPN exit IP B
    5. Run again — resumes from cache, processes next 500
    6. Repeat until --status reports complete

Key properties:
    - Idempotent: never re-fetches a component already cached. Re-running
      with --mode comprehensive after a --mode basic run only fetches the
      missing-mode components.
    - Atomic writes: components write to .tmp sibling, rename on success.
      Interrupted writes leave NO incomplete cache files.
    - Order: parcels processed in deterministic sorted order so resume works.
    - Auto-abort: monitors HTTP-error rate over a sliding window. If it
      crosses the threshold, exits with a clear "VPN may be blocked" message
      so the user can swap and restart.

Modes:
    basic         — 1 m4.cgi (with hist=1) per parcel. Captures sqft, year built,
                    style, sales summary, 8-year assessment history.
    comprehensive — basic + 1 sr.cgi per known historical sale (covers grantor/
                    grantee + family-sale flag + assessor REMARKS).

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

DISTRICT = "1314"  # Fair Haven NJGIN code

# Each parcel produces these component files in the output dir:
#   {pams_pin}/m4.html      — m4.cgi&hist=1 response (basic + comprehensive)
#   {pams_pin}/sr.html      — sr.cgi response (comprehensive only; per parcel,
#                              not per sale — sr.cgi shows the most recent
#                              recorded sale by default)
COMPONENT_M4 = "m4.html"
COMPONENT_SR = "sr.html"


@dataclass
class Config:
    parcels_path: Path
    output_root: Path
    mode: str               # "basic" or "comprehensive"
    batch_size: int
    rate_per_second: float
    jitter_pct: float
    max_error_rate: float   # e.g. 0.10 = 10%
    error_window: int       # number of recent requests to consider
    error_min_samples: int  # don't trip the abort until at least this many requests
    max_retries: int


@dataclass
class RunState:
    requests_done: int = 0
    cache_hits: int = 0
    fetched_ok: int = 0
    fetched_fail: int = 0
    retried: int = 0
    aborted: bool = False
    abort_reason: str | None = None
    recent_errors: deque = field(default_factory=lambda: deque(maxlen=200))


# ----------------------------------------------------------------------------
# Parcel ID encoding for OPRS deep-link URLs
# ----------------------------------------------------------------------------

def _pad(s: str, width: int) -> str:
    """Right-justify in a width-N field, padded with leading zeros if numeric,
    otherwise spaces — matches the OPRS l02 token convention."""
    s = (s or "").strip()
    if s.replace(".", "").isdigit():
        return s.zfill(width)
    return s.rjust(width)


def _split_block_lot(value: str) -> tuple[str, str]:
    """'77.01' → ('77', '01'); '15' → ('15', '')."""
    if "." in value:
        a, b = value.split(".", 1)
        return a, b
    return value, ""


def encode_l02(block: str, lot: str, qualifier: str = "") -> str:
    """Encode (block, lot, qualifier) → OPRS l02 URL parameter.

    Format (29 chars + trailing 'M'):
        DDDD BBBBB SSSS LLLLL ZZ QQQQQ M
        district(4) + block_base(5) + block_suffix(4) + lot_base(5) + lot_suffix(2) + qualifier(5) + 'M'

    Underscores are used as the padding character throughout (CGI-safe).
    Verified against live samples like '131400077____00080__02_____M'.
    """
    block_base, block_suffix = _split_block_lot(block)
    lot_base, lot_suffix = _split_block_lot(lot)

    parts = [
        DISTRICT,                               # 4
        block_base.zfill(5),                    # 5
        (block_suffix or "").ljust(4, "_"),     # 4
        lot_base.zfill(5),                      # 5
        (lot_suffix or "").ljust(2, "_"),       # 2
        (qualifier or "").ljust(5, "_"),        # 5
        "M",
    ]
    return "".join(parts)


def parse_pams_pin(pin: str) -> tuple[str, str, str]:
    """Inverse of canonical PAMS_PIN — return (block, lot, qualifier).
    PIN is '1314_BLOCK_LOT' or '1314_BLOCK_LOT_QUAL'.
    """
    parts = pin.split("_")
    if len(parts) == 3:
        return parts[1], parts[2], ""
    if len(parts) == 4:
        return parts[1], parts[2], parts[3]
    raise ValueError(f"unrecognized pams_pin: {pin!r}")


# ----------------------------------------------------------------------------
# Cache layout
# ----------------------------------------------------------------------------

def parcel_dir(output_root: Path, pams_pin: str) -> Path:
    return output_root / pams_pin


def required_components(mode: str) -> list[str]:
    if mode == "basic":
        return [COMPONENT_M4]
    if mode == "comprehensive":
        return [COMPONENT_M4, COMPONENT_SR]
    raise ValueError(f"unknown mode: {mode!r}")


def is_cached(output_root: Path, pams_pin: str, component: str) -> bool:
    p = parcel_dir(output_root, pams_pin) / component
    return p.exists() and p.stat().st_size > 100  # tombstone for tiny error pages


# ----------------------------------------------------------------------------
# HTTP fetch with atomic write
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
    except requests.RequestException as e:
        return 0, None


def _write_atomic(path: Path, data: bytes, min_size: int = 200) -> bool:
    """Write data to path via .tmp sibling. Returns True only if size meets
    the minimum sanity threshold AND rename succeeds. Otherwise leaves no
    file behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if len(data) < min_size:
        return False
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp, "wb") as f:
            f.write(data)
        tmp.replace(path)
        return True
    except OSError:
        tmp.unlink(missing_ok=True)
        return False


def fetch_component(
    session: requests.Session, pams_pin: str, component: str, output_root: Path,
    max_retries: int,
) -> tuple[bool, str]:
    """Fetch one component, atomic-write to cache. Returns (ok, status_string).

    status_string is a short tag for logging: 'cached', 'ok', 'http_404',
    'too_small', 'network_err', etc.
    """
    if is_cached(output_root, pams_pin, component):
        return True, "cached"

    block, lot, qualifier = parse_pams_pin(pams_pin)
    if component == COMPONENT_M4:
        l02 = encode_l02(block, lot, qualifier)
        url = f"{M4_BASE}?district={DISTRICT}&l02={l02}&hist=1"
    elif component == COMPONENT_SR:
        url = f"{SR_BASE}?&district={DISTRICT}&ms_user=&ssi=1331&block={block}&lot={lot}&qual={qualifier}"
    else:
        return False, f"unknown_component:{component}"

    last_status = "no_attempt"
    for attempt in range(max_retries):
        status_code, body = _fetch(session, url)
        if status_code == 0:
            last_status = "network_err"
            time.sleep(1.0 + attempt)
            continue
        if status_code != 200:
            last_status = f"http_{status_code}"
            time.sleep(1.0 + attempt)
            continue
        out = parcel_dir(output_root, pams_pin) / component
        if _write_atomic(out, body):
            return True, "ok"
        last_status = f"too_small:{len(body) if body else 0}"
        time.sleep(0.5)

    return False, last_status


# ----------------------------------------------------------------------------
# Workload planning
# ----------------------------------------------------------------------------

def load_parcel_ids(parcels_path: Path) -> list[str]:
    """Load PAMS_PINs from a parquet, parquet of geopandas, csv, or json file.
    Sorted ascending so resume order is deterministic."""
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


def plan_batch(
    parcel_ids: list[str], cfg: Config
) -> tuple[list[tuple[str, str]], dict[str, int]]:
    """Walk parcels in order; emit (pams_pin, component) pairs for missing
    components, up to batch_size. Returns (work_items, summary)."""
    components = required_components(cfg.mode)
    work: list[tuple[str, str]] = []
    summary = {"parcels_total": len(parcel_ids), "missing_components": 0,
               "fully_cached_parcels": 0}
    for pin in parcel_ids:
        all_cached = True
        for comp in components:
            if is_cached(cfg.output_root, pin, comp):
                continue
            all_cached = False
            summary["missing_components"] += 1
            if len(work) < cfg.batch_size:
                work.append((pin, comp))
        if all_cached:
            summary["fully_cached_parcels"] += 1
    return work, summary


# ----------------------------------------------------------------------------
# Run loop with error-rate monitoring
# ----------------------------------------------------------------------------

def _sleep_pacing(rate: float, jitter_pct: float) -> None:
    base = 1.0 / rate if rate > 0 else 0.0
    jitter = base * jitter_pct * (random.random() * 2 - 1)
    delay = max(0.05, base + jitter)
    time.sleep(delay)


def _check_abort(state: RunState, cfg: Config) -> tuple[bool, str | None]:
    """Return (should_abort, reason). Computes rolling error rate over the
    most recent error_window samples and trips if it exceeds max_error_rate
    after error_min_samples have been seen."""
    if cfg.error_window <= 0 or cfg.max_error_rate <= 0:
        return False, None
    samples = list(state.recent_errors)
    if len(samples) < cfg.error_min_samples:
        return False, None
    window = samples[-cfg.error_window:] if len(samples) >= cfg.error_window else samples
    error_count = sum(1 for ok in window if not ok)
    rate = error_count / len(window)
    if rate > cfg.max_error_rate:
        return True, (
            f"error rate {rate:.0%} ({error_count}/{len(window)}) exceeds "
            f"threshold {cfg.max_error_rate:.0%} — likely VPN/IP blocked. "
            f"Switch VPN exit and re-run."
        )
    return False, None


def run_batch(cfg: Config) -> RunState:
    state = RunState()
    log_path = cfg.output_root / "_collect.log"
    cfg.output_root.mkdir(parents=True, exist_ok=True)

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
    work, summary = plan_batch(parcel_ids, cfg)
    log(
        f"plan: parcels_total={summary['parcels_total']} "
        f"fully_cached={summary['fully_cached_parcels']} "
        f"missing_components={summary['missing_components']} "
        f"this_batch={len(work)}"
    )
    if not work:
        log("nothing to do — all components cached for selected mode")
        return state

    session = _new_session()
    for i, (pin, component) in enumerate(work, 1):
        ok, status = fetch_component(session, pin, component, cfg.output_root, cfg.max_retries)
        state.requests_done += 1
        state.recent_errors.append(ok)
        if status == "cached":
            state.cache_hits += 1
        elif ok:
            state.fetched_ok += 1
        else:
            state.fetched_fail += 1

        # Compact per-request log every 25 items
        if i % 25 == 0 or i == len(work):
            log(
                f"  [{i}/{len(work)}] last={pin}/{component} status={status} "
                f"ok={state.fetched_ok} fail={state.fetched_fail}"
            )

        should_abort, reason = _check_abort(state, cfg)
        if should_abort:
            state.aborted = True
            state.abort_reason = reason
            log(f"ABORT: {reason}")
            break

        _sleep_pacing(cfg.rate_per_second, cfg.jitter_pct)

    log(
        f"batch end: requests={state.requests_done} ok={state.fetched_ok} "
        f"fail={state.fetched_fail} cache_hits={state.cache_hits} "
        f"aborted={state.aborted}"
    )
    return state


# ----------------------------------------------------------------------------
# Status reporting
# ----------------------------------------------------------------------------

def report_status(cfg: Config) -> None:
    parcel_ids = load_parcel_ids(cfg.parcels_path)
    components = required_components(cfg.mode)
    fully_cached = 0
    component_counts = {c: 0 for c in components}
    for pin in parcel_ids:
        all_ok = True
        for comp in components:
            if is_cached(cfg.output_root, pin, comp):
                component_counts[comp] += 1
            else:
                all_ok = False
        if all_ok:
            fully_cached += 1
    total = len(parcel_ids)
    print(f"OPRS cache status — mode={cfg.mode} output={cfg.output_root}")
    print(f"  parcels_total: {total}")
    print(f"  parcels_complete (all components for mode): {fully_cached} ({100*fully_cached/total:.1f}%)")
    for c, n in component_counts.items():
        print(f"  component {c:12s}: {n}/{total} ({100*n/total:.1f}%)")
    missing = sum(total - n for n in component_counts.values())
    print(f"  total missing component fetches needed: {missing}")
    print(f"  estimated batches at batch={cfg.batch_size}: {-(-missing // cfg.batch_size)}")


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(
        description="Collect Fair Haven OPRS Property Record Card data "
        "(batch-based, VPN-swap friendly, idempotent, atomic).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--parcels-from", type=Path, default=PARCELS_DEFAULT,
                   help="Parquet/CSV/JSON file with PAMS_PINs (column 'pams_pin')")
    p.add_argument("--output-dir", type=Path, default=OUTPUT_DEFAULT,
                   help="Cache root. Each parcel gets a subdir.")
    p.add_argument("--mode", choices=["basic", "comprehensive"], default="basic",
                   help="basic = m4.cgi only; comprehensive = m4 + sr (sale detail)")
    p.add_argument("--batch", dest="batch_size", type=int, default=500,
                   help="Max requests per invocation (then exit cleanly)")
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
                   help="Print cache status for the given parcels and exit")
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
