"""Parse OPRS Property Record Card PDF → 30-field dict (D-32 PRC subset).

The PRC PDF is the only data source carrying parcel-level structural fields
(bedrooms, bathrooms, condition, quality grade, foundation, exterior, roof,
heating, AC, story breakdown) for Fair Haven. Phase 2 hedonic depends on
this parser.

Text-extraction strategy: pdfplumber (with pdfminer.six fallback for
MediaBox-missing PDFs — see datasets/collect_oprs.py::_pdfplumber_page1_ok),
regex-based field extraction against the joined-page text.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber

PRC_PDF_FIELDS = [
    # Room counts (ints)
    "bedrooms",
    "bathrooms",
    "room_count",
    "kitchens",
    # Area (Decimal, sqft) + age (int)
    "livable_area",
    "eff_age",
    # Story breakdown (Decimal sqft)
    "first_story_sf",
    "upper_story_sf",
    "half_story_sf",
    # Categorical building attributes (uppercase strings)
    "condition",
    "quality_grade",
    "foundation",
    "exterior",
    "roof_type",
    "roof_material",
    # Heating / AC (string + Decimal sqft)
    "heating_type",
    "heating_sf",
    "ac_type",
    "ac_sf",
    # Misc structural
    "fireplaces",
    "garage_type",
    "garage_sf",
    "porch_sf",
    "patio_sf",
    "shed_sf",
    # Site (uppercase strings)
    "sewer",
    "water",
    "gas",
    "topography",
    "road_type",
]


def _to_decimal(v) -> Decimal | None:
    if v is None:
        return None
    try:
        s = str(v).strip().replace("$", "").replace(",", "")
        if s.lower() in {"nan", "none", ""}:
            return None
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _to_int(v) -> int | None:
    if v is None:
        return None
    try:
        s = str(v).strip()
        if s.lower() in {"nan", "none", ""}:
            return None
        n = int(float(s))
        return n if n > 0 else None
    except (ValueError, TypeError):
        return None


def _extract_text(path: Path) -> str:
    """Extract all-page text via pdfplumber; fall back to pdfminer.six on MediaBox errors."""
    try:
        with pdfplumber.open(str(path)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        joined = "\n".join(pages)
        if joined.strip():
            return joined
    except Exception:
        pass
    # Fallback: pdfminer.six handles missing-MediaBox PDFs gracefully.
    try:
        from pdfminer.high_level import extract_text

        return extract_text(str(path)) or ""
    except Exception:
        return ""


# --- Regex constants -------------------------------------------------------

# "Room Count: Tot: 7 Bed: 3 Bth: 2"
_ROOM_COUNT_RE = re.compile(
    r"Room\s+Count:\s*Tot:\s*(\d+)\s*Bed:\s*(\d+)\s*Bth:\s*(\d+)",
    re.I,
)
# "Bath: Mod:1 Avg:1 Old:"  (each segment may be blank)
_BATH_BREAKDOWN_RE = re.compile(
    r"Bath:\s*Mod:\s*(\d*)\s*Avg:\s*(\d*)\s*Old:\s*(\d*)",
    re.I,
)
# "Kitchen: Mod: Avg:1 Old:"
_KITCHEN_BREAKDOWN_RE = re.compile(
    r"Kitchen:\s*Mod:\s*(\d*)\s*Avg:\s*(\d*)\s*Old:\s*(\d*)",
    re.I,
)
_LIVABLE_AREA_RE = re.compile(r"Livable\s+Area:\s*([\d,]+)", re.I)
_EFF_AGE_RE = re.compile(r"Eff\s+Age\s*\(Years\):\s*(\d+)", re.I)

# Story breakdown lines look like "FIRST STORY 986 SF", "UPPER STORY 756 SF",
# "HALF STORY 36"  (note: HALF STORY may omit "SF").
_FIRST_STORY_RE = re.compile(r"FIRST\s+STORY\s+([\d,]+)\s*SF", re.I)
_UPPER_STORY_RE = re.compile(r"UPPER\s+STORY\s+([\d,]+)\s*SF", re.I)
_HALF_STORY_RE = re.compile(r"HALF\s+STORY\s+([\d,]+)", re.I)

# Categorical: "Condition: NORMAL", "Foundation: CONCRETE BLOCK",
# "Exterior Fin: FRAME", "Roof Type: GABLE", "Roof Material: SHINGLE"
_CONDITION_RE = re.compile(r"Condition:\s*([A-Z][A-Z /]+?)(?:\s{2,}|\n|$)", re.I)
_FOUNDATION_RE = re.compile(r"Foundation:\s*([A-Z][A-Z /]+?)(?:\s{2,}|\n|$)", re.I)
_EXTERIOR_RE = re.compile(r"Exterior\s+Fin:\s*([A-Z][A-Z /]+?)(?:\s{2,}|\n|$)", re.I)
_ROOF_TYPE_RE = re.compile(r"Roof\s+Type:\s*([A-Z][A-Z /]+?)(?:\s{2,}|\n|$)", re.I)
_ROOF_MATERIAL_RE = re.compile(r"Roof\s+Material:\s*([A-Z][A-Z /]+?)(?:\s{2,}|\n|$)", re.I)
# "Quality: 18 822 2" — first token after the label is the grade code.
_QUALITY_RE = re.compile(r"Quality:\s*([A-Z0-9+\-]+)", re.I)

# Site lines: "Sewer: SEW/WATER", "Water:", "Gas: SEWER ONLY",
# "Topography: LEVEL", "Road: PAVED"
_SEWER_RE = re.compile(r"Sewer:\s*([A-Z][A-Z /]*?)(?:\s*\n|$)", re.I)
_WATER_RE = re.compile(r"Water:\s*([A-Z][A-Z /]*?)(?:\s*\n|$)", re.I)
_GAS_RE = re.compile(r"Gas:\s*([A-Z][A-Z /]*?)(?:\s*\n|$)", re.I)
_TOPOGRAPHY_RE = re.compile(r"Topography:\s*([A-Z][A-Z /]*?)(?:\s*\n|$)", re.I)
_ROAD_RE = re.compile(r"Road:\s*([A-Z][A-Z /]*?)(?:\s*\n|$)", re.I)

# Heating / AC inline lines:
#   "FORCED HOT AIR 1763 SF"
#   "AC (COMB DUCTS) 1763 SF"
#   "ELECTRIC BASEBOARD 800 SF"
_HEATING_LINE_RE = re.compile(
    r"^(?!AC\b)([A-Z][A-Z /\-]*?(?:HOT\s+(?:AIR|WATER)|HEAT|BASEBOARD|FURNACE|STEAM|RADIANT)[A-Z /\-]*)\s+([\d,]+)\s*SF",
    re.I | re.M,
)
_AC_LINE_RE = re.compile(
    r"^(AC\s*\([A-Z /\-]+\)|CENTRAL\s+AC|AC\s+[A-Z /\-]+?)\s+([\d,]+)\s*SF",
    re.I | re.M,
)

# Fireplaces: "FIREPLACE 2STY 1"  or "FIREPLACE 1"
_FIREPLACE_RE = re.compile(r"FIREPLACE[A-Z0-9 ]*?\s+(\d+)\s*$", re.I | re.M)

# Garage: "GARAGE ATTACHED 400 SF" / "GARAGE 1 STY 200 SF"
_GARAGE_LINE_RE = re.compile(
    r"^(GARAGE[A-Z0-9 \-]*?)\s+([\d,]+)\s*SF",
    re.I | re.M,
)

# Porch / Patio / Shed: similar pattern
_PORCH_RE = re.compile(r"PORCH[A-Z0-9 \-]*?\s+([\d,]+)\s*SF", re.I)
_PATIO_RE = re.compile(r"PATIO[A-Z0-9 \-]*?\s+([\d,]+)\s*SF", re.I)
_SHED_RE = re.compile(r"SHED[A-Z0-9 \-]*?\s+([\d,]+)\s*SF", re.I)


def _first_match(rx: re.Pattern[str], text: str, group: int = 1) -> str | None:
    m = rx.search(text)
    if not m:
        return None
    val = m.group(group).strip()
    return val or None


def _norm_upper(s: str | None) -> str | None:
    if s is None:
        return None
    s = re.sub(r"\s+", " ", s).strip().upper()
    return s or None


def _sum_breakdown(rx: re.Pattern[str], text: str) -> int | None:
    """Sum mod/avg/old breakdown digits; return None if no match found."""
    m = rx.search(text)
    if not m:
        return None
    total = 0
    saw_any = False
    for token in m.groups():
        token = (token or "").strip()
        if token.isdigit():
            total += int(token)
            saw_any = True
    return total if saw_any else None


def parse_prc_pdf(path: Path) -> dict[str, object]:
    """Parse one OPRS Property Record Card PDF → canonical 30-field dict (D-32).

    All keys in PRC_PDF_FIELDS are present in the result; missing fields are
    None. Returns a dict of all-None values when the PDF is unparseable
    (graceful — caller decides whether to drop the row).

    Args:
        path: Path to a prc.pdf file (already header-stripped per D-28).

    Returns:
        dict[str, object]: keys = PRC_PDF_FIELDS; values are int / Decimal /
        uppercase str / None depending on the field semantics.
    """
    path = Path(path)
    text = _extract_text(path)
    result: dict[str, object] = {k: None for k in PRC_PDF_FIELDS}
    if not text.strip():
        return result

    # Room count line (Tot/Bed/Bth) — single regex, three captures.
    m = _ROOM_COUNT_RE.search(text)
    if m:
        result["room_count"] = _to_int(m.group(1))
        result["bedrooms"] = _to_int(m.group(2))
        result["bathrooms"] = _to_int(m.group(3))

    # Bath count breakdown — also reflects bathroom count via mod+avg+old sum.
    # Prefer the Room Count "Bth:" value (more authoritative) but use the
    # breakdown as fallback when Room Count is missing.
    if result["bathrooms"] is None:
        result["bathrooms"] = _sum_breakdown(_BATH_BREAKDOWN_RE, text)
    result["kitchens"] = _sum_breakdown(_KITCHEN_BREAKDOWN_RE, text)

    # Areas / age
    result["livable_area"] = _to_decimal(_first_match(_LIVABLE_AREA_RE, text))
    result["eff_age"] = _to_int(_first_match(_EFF_AGE_RE, text))
    result["first_story_sf"] = _to_decimal(_first_match(_FIRST_STORY_RE, text))
    result["upper_story_sf"] = _to_decimal(_first_match(_UPPER_STORY_RE, text))
    result["half_story_sf"] = _to_decimal(_first_match(_HALF_STORY_RE, text))

    # Categorical
    result["condition"] = _norm_upper(_first_match(_CONDITION_RE, text))
    result["foundation"] = _norm_upper(_first_match(_FOUNDATION_RE, text))
    result["exterior"] = _norm_upper(_first_match(_EXTERIOR_RE, text))
    result["roof_type"] = _norm_upper(_first_match(_ROOF_TYPE_RE, text))
    result["roof_material"] = _norm_upper(_first_match(_ROOF_MATERIAL_RE, text))
    result["quality_grade"] = _norm_upper(_first_match(_QUALITY_RE, text))

    # Site
    result["sewer"] = _norm_upper(_first_match(_SEWER_RE, text))
    result["water"] = _norm_upper(_first_match(_WATER_RE, text))
    result["gas"] = _norm_upper(_first_match(_GAS_RE, text))
    result["topography"] = _norm_upper(_first_match(_TOPOGRAPHY_RE, text))
    result["road_type"] = _norm_upper(_first_match(_ROAD_RE, text))

    # Heating
    m = _HEATING_LINE_RE.search(text)
    if m:
        result["heating_type"] = _norm_upper(m.group(1))
        result["heating_sf"] = _to_decimal(m.group(2))

    # AC
    m = _AC_LINE_RE.search(text)
    if m:
        result["ac_type"] = _norm_upper(m.group(1))
        result["ac_sf"] = _to_decimal(m.group(2))

    # Fireplaces — "FIREPLACE 2STY 1"
    m = _FIREPLACE_RE.search(text)
    if m:
        result["fireplaces"] = _to_int(m.group(1))

    # Garage / porch / patio / shed
    m = _GARAGE_LINE_RE.search(text)
    if m:
        result["garage_type"] = _norm_upper(m.group(1))
        result["garage_sf"] = _to_decimal(m.group(2))
    result["porch_sf"] = _to_decimal(_first_match(_PORCH_RE, text))
    result["patio_sf"] = _to_decimal(_first_match(_PATIO_RE, text))
    result["shed_sf"] = _to_decimal(_first_match(_SHED_RE, text))

    return result
