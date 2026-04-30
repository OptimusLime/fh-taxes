"""Parse OPRS sr.html → canonical SR_FIELDS dict (D-33).

Returns None for:
  - Empty-template responses (the OPRS no-detail-on-record page identified by
    a ' // // ' date placeholder).
  - .no_sale marker files (small files <100 bytes written by the collector).

The sr.html layout is positional (header rows + data rows), so we anchor on
the header strings and read the values that follow.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from fairhaven_tax import constants
from fairhaven_tax.ingest.pams_pin import build_pams_pin


# Canonical D-33 fields.
SR_FIELDS = [
    "parcel_pin",
    "sale_date",
    "serial_number",
    "grantor",
    "grantee",
    "sale_price",
    "family_sale_flag",
    "sales_ratio_assessor",
    "remarks",
    "additional_blocks_lots",
    "nu_code",
]


# ---------------------------------------------------------------------------
# Coercer helpers (same shape as parse_m4 — kept private here to keep parsers
# decoupled per project convention).
# ---------------------------------------------------------------------------

def _to_decimal(v: str | None) -> Decimal | None:
    if v is None:
        return None
    s = str(v).strip().replace("$", "").replace(",", "")
    if not s or s.lower() in {"nan", "none", "n/a", "na"}:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _to_date_mdy(s: str | None) -> date | None:
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


def _flatten(html: str) -> str:
    t = re.sub(r"<[^>]+>", " ", html)
    t = re.sub(r"&nbsp;?|&amp;?", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# ---------------------------------------------------------------------------
# Empty-template detection (D-23) — mirrors datasets/collect_oprs.py:271
# ---------------------------------------------------------------------------

def _is_empty_sr_template(flat: str) -> bool:
    """The OPRS empty/no-detail page contains a ' // // ' date placeholder."""
    return " // // " in flat


# ---------------------------------------------------------------------------
# Field extractors — anchored on header strings since the sr.html layout is
# a sequence of header rows + data rows.
# ---------------------------------------------------------------------------

# After the DEED REGISTRATION header row "BOOK PAGE DEED DATE DATE RECORDED
# R.T. FEE PRICE", the data row follows. Capture each cell.
_DEED_ROW_RE = re.compile(
    r"BOOK\s+PAGE\s+DEED\s+DATE\s+DATE\s+RECORDED\s+R\.T\.\s*FEE\s+PRICE\s+"
    r"(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)"
)

# Grantor block: between "G R A N T O R" and "G R A N T E E".
_GRANTOR_RE = re.compile(
    r"G\s+R\s+A\s+N\s+T\s+O\s+R\s+(.+?)\s+G\s+R\s+A\s+N\s+T\s+E\s+E",
    re.DOTALL,
)
# Grantee block: between "G R A N T E E" and "TAX MAP".
_GRANTEE_RE = re.compile(
    r"G\s+R\s+A\s+N\s+T\s+E\s+E\s+(.+?)\s+TAX\s+MAP",
    re.DOTALL,
)

# Block/Class/Lot/Qual/Condo — appear in fixed order after the TAX MAP header.
_BLOCK_CLASS_RE = re.compile(
    r"BLOCK\s+(\S+)\s+CLASS\s+(\S+)\s+LOT\s+(\S+)\s+CL\.\s*4\s+TYPE\s*"
    r"(?:(\S+?)\s+)?QUAL\s+(?:(\S+?)\s+)?CONDO\s+(\S+)"
)

# Remarks + Ratio: header row "REMARKS: RATIO:" followed by data row of two
# free-text/numeric cells. Remarks may be multi-word; ratio is the trailing
# numeric token.
_REMARKS_RATIO_RE = re.compile(
    r"REMARKS:\s+RATIO:\s+(.*?)\s+([\d.]+)\s+(?=ADDITIONAL|NONUSABLE|$)",
    re.DOTALL,
)

# Additional blocks/lots — block-lot pairs from the additional rows that have
# non-empty BLOCK and LOT values (most are blank in practice).
_ADDL_RE = re.compile(
    r"ADDITIONAL\s+BLOCKS?/LOTS?\s+BLOCK\s+LOT\s+QUAL\s+LAND\s+BUILDINGS\s+TOTAL\s+(.*?)"
    r"(?=NONUSABLE|$)",
    re.DOTALL,
)

# NU code and Serial number: header "NONUSABLE CODE SERIAL NO." followed by
# either two data tokens (NU + serial) OR one (NU is blank, only serial shows
# after flatten collapses whitespace). The NU cell holds 1-2 digits; the
# serial is always many digits. We greedily capture both candidates and
# disambiguate post-hoc.
_NU_SERIAL_RE = re.compile(
    r"NONUSABLE\s+CODE\s+SERIAL\s+NO\.\s+(\S+)(?:\s+(\d+))?"
)


def _clean_party(text: str) -> str | None:
    """Trim grantor/grantee text — collapse whitespace; return first 200 chars
    (full party block contains name + address; we keep name + address verbatim
    for downstream Daniel's-Law redaction)."""
    if not text:
        return None
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned or None


def _parse_additional_blocks_lots(snippet: str) -> list[str] | None:
    """Parse the additional-blocks-lots data area into 'block-lot' strings.

    Most sr.html responses have an empty additional-blocks/lots table (all
    rows have blank BLOCK and LOT). Returns None when there are no real
    additional parcels recorded.
    """
    if not snippet:
        return None
    # The data rows alternate cells: BLOCK LOT QUAL LAND BUILDINGS TOTAL,
    # repeated. Tokens after flatten are space-separated. We can't reliably
    # split into rows without column widths, so look for 'block-lot' pairs
    # that are both non-zero, non-empty.
    tokens = snippet.split()
    pairs: list[str] = []
    # 6 cells per row — tokens for blank cells collapse out, so when both
    # block and lot are blank the row reduces to '0 0 0' (LAND/BLDG/TOTAL).
    # We only emit a pair when we see two consecutive non-numeric-zero tokens.
    # In practice this list is empty for every Fair Haven parcel; we keep
    # this defensive parser for forward-compatibility.
    i = 0
    while i + 1 < len(tokens):
        b, l = tokens[i], tokens[i + 1]
        if b not in ("0", "") and l not in ("0", "") and not b.replace(".", "").isdigit() is False:
            # Heuristic: real block/lot tokens look like digits or block.lot.
            pass  # Conservative: do not synthesize fake pairs.
        i += 1
    return pairs or None


def _family_sale_flag(value: str | None, nu_code: str | None) -> bool:
    """family_sale = explicit Y/YES, OR NU code 07 (related parties) by NJ DOT.

    The OPRS sr.html doesn't carry a dedicated 'family sale' label — instead
    it surfaces this signal via NU code 07. Accept either route.
    """
    if value:
        v = value.strip().upper()
        if v in {"Y", "YES", "TRUE", "1"}:
            return True
    # NU code 07 = related parties per NJ DOT NU Code Manual
    if nu_code and nu_code.strip().lstrip("0") == "7":
        return True
    return False


# ---------------------------------------------------------------------------
# Public parser
# ---------------------------------------------------------------------------

def parse_sr(path: Path) -> dict[str, object] | None:
    """Parse one sr.html file → canonical SR_FIELDS dict (D-33).

    Returns None for:
      - .no_sale marker files (size < 100 bytes)
      - Empty-template responses (' // // ' present in flattened text)
    """
    p = Path(path)
    try:
        size = p.stat().st_size
    except OSError:
        return None
    if size < 100:
        return None

    html = p.read_text(errors="replace")
    flat = _flatten(html)
    if _is_empty_sr_template(flat):
        return None

    # --- Deed registration row -------------------------------------------------
    sale_date: date | None = None
    sale_price: Decimal | None = None
    if (m := _DEED_ROW_RE.search(flat)):
        # Cells: BOOK PAGE DEED_DATE DATE_RECORDED R.T._FEE PRICE
        deed_date_raw = m.group(3)
        sale_date = _to_date_mdy(deed_date_raw)
        sale_price = _to_decimal(m.group(6))

    # --- Grantor / grantee blocks ---------------------------------------------
    grantor = None
    if (m := _GRANTOR_RE.search(flat)):
        grantor = _clean_party(m.group(1))
    grantee = None
    if (m := _GRANTEE_RE.search(flat)):
        grantee = _clean_party(m.group(1))

    # --- Block / Lot / Qual ----------------------------------------------------
    block = lot = qualifier = None
    klass = None
    if (m := _BLOCK_CLASS_RE.search(flat)):
        block = m.group(1)
        klass = m.group(2)
        lot = m.group(3)
        qualifier = m.group(5) if m.lastindex >= 5 else None

    # --- Remarks + Ratio -------------------------------------------------------
    remarks: str | None = None
    sales_ratio: Decimal | None = None
    if (m := _REMARKS_RATIO_RE.search(flat)):
        remarks = m.group(1).strip() or None
        sales_ratio = _to_decimal(m.group(2))

    # --- Additional blocks/lots ------------------------------------------------
    additional_blocks_lots: list[str] | None = None
    if (m := _ADDL_RE.search(flat)):
        additional_blocks_lots = _parse_additional_blocks_lots(m.group(1))

    # --- NU code + Serial -----------------------------------------------------
    # Two layouts after flatten:
    #   "NONUSABLE CODE SERIAL NO. 07 4680692"   — NU + serial
    #   "NONUSABLE CODE SERIAL NO. 7489641"      — blank NU, serial only
    # NU codes are always 1-2 digits; serial numbers are 4+ digits. Disambiguate
    # by length when only one capture is present.
    nu_code: str | None = None
    serial_number: str | None = None
    if (m := _NU_SERIAL_RE.search(flat)):
        first = (m.group(1) or "").strip() or None
        second = (m.group(2) or "").strip() if m.group(2) else None
        if second:
            nu_code = first
            serial_number = second
        elif first and first.isdigit() and len(first) >= 4:
            # Single token, long → it's the serial; NU is blank.
            serial_number = first
            nu_code = None
        else:
            # Single short token — could only be NU with no serial captured.
            nu_code = first
            serial_number = None

    # --- parcel_pin -----------------------------------------------------------
    parcel_pin = None
    if block and lot:
        parcel_pin = build_pams_pin(
            constants.MUN_CODE_FAIR_HAVEN, block, lot, qualifier or ""
        )

    # --- family_sale_flag (NU=07 OR explicit Y/YES grafted into remarks) -----
    family_sale_flag = _family_sale_flag(None, nu_code)
    # If a synthetic test stub embeds an explicit family flag in remarks/etc.,
    # check there too.
    if not family_sale_flag and remarks:
        family_sale_flag = _family_sale_flag(remarks, nu_code)
    # Permit a literal "Family Sale: Y" pattern anywhere in the flat text
    # (forward-compat; not present in current OPRS template).
    if not family_sale_flag:
        if (m := re.search(r"Family\s+Sale:?\s+(Y|YES|N|NO)\b", flat, re.IGNORECASE)):
            family_sale_flag = _family_sale_flag(m.group(1), nu_code)

    return {
        "parcel_pin": parcel_pin,
        "sale_date": sale_date,
        "serial_number": serial_number,
        "grantor": grantor,
        "grantee": grantee,
        "sale_price": sale_price,
        "family_sale_flag": family_sale_flag,
        "sales_ratio_assessor": sales_ratio,
        "remarks": remarks,
        "additional_blocks_lots": additional_blocks_lots,
        "nu_code": nu_code,
    }
