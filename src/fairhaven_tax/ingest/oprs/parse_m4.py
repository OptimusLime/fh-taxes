"""Parse OPRS m4.html → canonical M4_FIELDS dict (D-32 m4 subset).

Pure function: takes a Path, returns a dict with every M4_FIELDS key present
(None for missing). Mirrors the shape of `src/fairhaven_tax/ingest/sr1a/parse.py`.

The OPRS m4 page is a series of <td>label</td><td>value</td> pairs across
several tables. After flattening the HTML to plain text we extract each field
by matching `LabelName: VALUE` where VALUE is bounded by the next known label
or known terminator.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from fairhaven_tax import constants
from fairhaven_tax.ingest.pams_pin import build_pams_pin


# Canonical D-32 m4 subset.
M4_FIELDS = [
    "pams_pin",
    "block",
    "lot",
    "qualifier",
    "prop_loc",
    "square_ft",
    "year_built",
    "style_code",
    "bldg_desc",
    "land_desc",
    "acreage",
    "zone",
    "map_page",
    "class",
    "current_taxes_1h",
    "current_taxes_2h",
    "updated_date",
]


# All m4 label tokens we know about. Used as boundary anchors so that a
# value-extraction regex stops at the next label rather than spilling into
# adjacent cells. The order is irrelevant — we OR them in the regex.
_M4_LABELS = (
    "Block", "Lot", "Qual", "Prop Loc", "Owner", "Square Ft", "District",
    "Street", "Year Built", "Class", "City State", "Style",
    "Prior Block", "Acct Num", "Addl Lots", "EPL Code",
    "Prior Lot", "Mtg Acct", "Land Desc", "Statute",
    "Prior Qual", "Bank Code", "Bldg Desc", "Initial", "Further",
    "Updated", "Tax Codes", "Class4Cd", "Desc",
    "Zone", "Map Page", "Acreage", "Taxes",
    "Sale Date", "Book", "Page", "Price", "NU#",
)
_LABEL_ALT = "|".join(re.escape(lbl) for lbl in _M4_LABELS)


# ---------------------------------------------------------------------------
# Coercer helpers (mirrors src/fairhaven_tax/ingest/sr1a/parse.py + ingest_njgin)
# ---------------------------------------------------------------------------

def _to_decimal(v: str | None) -> Decimal | None:
    """Coerce a string with optional $ and , into Decimal. Empty/N/A → None."""
    if v is None:
        return None
    s = str(v).strip().replace("$", "").replace(",", "")
    if not s or s.lower() in {"nan", "none", "n/a", "na"}:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _to_int(v: str | None) -> int | None:
    """Coerce a string into an int. Empty / non-numeric → None. Zero → None."""
    if v is None:
        return None
    s = str(v).strip().replace(",", "")
    if not s or s.lower() in {"nan", "none", "n/a", "na"}:
        return None
    if not s.lstrip("-").isdigit():
        return None
    try:
        n = int(s)
    except ValueError:
        return None
    return n if n > 0 else None


def _to_date_mdy(s: str | None) -> date | None:
    """Parse 'MM/DD/YY' or 'MM/DD/YYYY'. NJ convention: 2-digit year < 50 → 20xx."""
    if not s:
        return None
    s = s.strip()
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", s)
    if not m:
        return None
    mm, dd, yy = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if yy < 100:
        yy = 2000 + yy if yy < 50 else 1900 + yy
    try:
        return date(yy, mm, dd)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# HTML flatten
# ---------------------------------------------------------------------------

def _flatten(html: str) -> str:
    """Mirror datasets/collect_oprs.py::_validate flatten — strip tags, normalize.

    OPRS templates write &nbsp without the trailing semicolon (HTML4 quirk),
    so handle both `&nbsp` and `&nbsp;` plus `&amp(;)?` defensively.
    """
    t = re.sub(r"<[^>]+>", " ", html)
    t = re.sub(r"&nbsp;?|&amp;?", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# ---------------------------------------------------------------------------
# ssi enumeration (re-uses datasets/collect_oprs.py:207 pattern)
# ---------------------------------------------------------------------------

_SSI_RE = re.compile(
    r'sr\.cgi\?[^"\']*?ssi=(\d+)[^"\']*?block=(\d+)[^"\']*?lot=(\d+)'
)


def extract_ssis(m4_text: str) -> list[str]:
    """Pull sale-detail serial numbers from an m4.html page.

    Matches the collector's regex (`datasets/collect_oprs.py:207`). Returns
    ssi values in document order, deduplicated.
    """
    seen: list[str] = []
    for m in _SSI_RE.finditer(m4_text):
        ssi = m.group(1)
        if ssi not in seen:
            seen.append(ssi)
    return seen


# ---------------------------------------------------------------------------
# Field extractors
# ---------------------------------------------------------------------------

def _extract(flat: str, label: str) -> str | None:
    """Extract the value following `Label:` up to the next known label.

    Returns the trimmed value, or None when the label is absent. An empty
    captured value (label present, no value) returns None.
    """
    # Lookahead allows zero-or-more whitespace before the next label so that
    # an empty value (e.g. `Qual: Class: 2`) terminates immediately rather
    # than swallowing the next label/value pair.
    pattern = (
        rf"\b{re.escape(label)}:\s*"
        rf"(.*?)"
        rf"(?=\s*(?:{_LABEL_ALT}):|$)"
    )
    m = re.search(pattern, flat)
    if not m:
        return None
    val = m.group(1).strip()
    return val or None


_TAX_PAIR_RE = re.compile(
    r"\$?\s*([\d,]+(?:\.\d+)?)\s*/\s*\$?\s*([\d,]+(?:\.\d+)?)"
)


def _extract_taxes(flat: str) -> tuple[Decimal | None, Decimal | None]:
    """Taxes field is rendered as '$NNNN.NN / $NNNN.NN' (1H / 2H).

    The Taxes label sits at the end of the m4 summary table immediately before
    the 'Sale Information' section header, which has no colon — so we cannot
    rely on label-boundary lookahead alone. Match the numeric pair directly.
    """
    raw = _extract(flat, "Taxes")
    if not raw:
        return None, None
    m = _TAX_PAIR_RE.search(raw)
    if not m:
        # Sometimes only a single value present.
        single = _to_decimal(raw.split()[0]) if raw.split() else None
        return single, None
    return _to_decimal(m.group(1)), _to_decimal(m.group(2))


# ---------------------------------------------------------------------------
# Public parser
# ---------------------------------------------------------------------------

def parse_m4(path: Path) -> dict[str, object]:
    """Parse one m4.html file → canonical M4_FIELDS dict (D-32 m4 subset).

    Returns a dict with every M4_FIELDS key present. Missing fields are None.
    Numeric/date fields are coerced; raw-text fields are returned trimmed.
    """
    html = Path(path).read_text(errors="replace")
    flat = _flatten(html)

    block = _extract(flat, "Block")
    lot = _extract(flat, "Lot")
    qualifier = _extract(flat, "Qual")
    prop_loc = _extract(flat, "Prop Loc")
    square_ft = _to_int(_extract(flat, "Square Ft"))
    year_built = _to_int(_extract(flat, "Year Built"))
    style_code = _extract(flat, "Style")
    bldg_desc = _extract(flat, "Bldg Desc")
    land_desc = _extract(flat, "Land Desc")
    acreage = _to_decimal(_extract(flat, "Acreage"))
    zone = _extract(flat, "Zone")
    map_page = _extract(flat, "Map Page")
    klass = _extract(flat, "Class")
    taxes_1h, taxes_2h = _extract_taxes(flat)
    updated_date = _to_date_mdy(_extract(flat, "Updated"))

    # PAMS_PIN — built from rendered block/lot/qual via shared helper.
    if block and lot:
        pams_pin = build_pams_pin(
            constants.MUN_CODE_FAIR_HAVEN, block, lot, qualifier or ""
        )
    else:
        pams_pin = None

    return {
        "pams_pin": pams_pin,
        "block": block,
        "lot": lot,
        "qualifier": qualifier,
        "prop_loc": prop_loc,
        "square_ft": square_ft,
        "year_built": year_built,
        "style_code": style_code,
        "bldg_desc": bldg_desc,
        "land_desc": land_desc,
        "acreage": acreage,
        "zone": zone,
        "map_page": map_page,
        "class": klass,
        "current_taxes_1h": taxes_1h,
        "current_taxes_2h": taxes_2h,
        "updated_date": updated_date,
    }
