"""PAMS_PIN construction. The join key across NJGIN and SR1A.

NJGIN canonical format (verified against parcels_gdb_Monmouth.zip 2026-04-29):
    f"{muni_code}_{block}_{lot}"            when qualifier is empty
    f"{muni_code}_{block}_{lot}_{qualifier}" when qualifier is present

Where:
    muni_code:  4-digit string (county + district), e.g. "1314" for Fair Haven
    block:      verbatim block (may include "." like "77.01" for sub-blocks)
    lot:        verbatim lot   (may include "." like "15.01" for subdivided lots)
    qualifier:  e.g. "C0001" for condo unit; absent for most parcels

SR1A ships block/lot zero-padded to 5 chars with separate 4-char suffix fields.
The reconstruction rule (verified against Sales2025.txt):
    BLOCK="00077", BLOCK_SUFFIX="01"  →  block "77.01"
    LOT="00080", LOT_SUFFIX="02"      →  lot "80.02"
    BLOCK="00077", BLOCK_SUFFIX=""    →  block "77"
"""
from __future__ import annotations


def _strip_leading_zeros(s: str) -> str:
    """Return integer-portion with leading zeros stripped, preserving '0' for '00000'."""
    s = s.strip()
    if not s:
        return ""
    stripped = s.lstrip("0")
    return stripped if stripped else "0"


def _join_suffix(base: str, suffix: str) -> str:
    """Combine a base value with an optional dotted suffix (SR1A → NJGIN style).

    SR1A right-justifies suffix in a 4-char field, sometimes producing a single
    digit like '1'. NJGIN uses 2-digit minimum padding ('.01', '.02'). We
    left-pad numeric suffixes to width 2 to match NJGIN convention.
    """
    base = _strip_leading_zeros(base)
    suffix = (suffix or "").strip()
    if not suffix or suffix == "0" * len(suffix):
        return base
    if suffix.isdigit() and len(suffix) < 2:
        suffix = suffix.zfill(2)
    return f"{base}.{suffix}"


def build_pams_pin(
    muni_code: str,
    block: str,
    lot: str,
    qualifier: str | None = None,
    *,
    block_suffix: str = "",
    lot_suffix: str = "",
) -> str:
    """Build a canonical NJGIN-style PAMS_PIN.

    Args:
        muni_code: 4-digit string like "1314" (Fair Haven). Pass full muni code,
            NOT the 2-digit district code.
        block: MOD-IV / SR1A block. Leading zeros are stripped.
        lot:   MOD-IV / SR1A lot. Leading zeros are stripped.
        qualifier: MOD-IV qualifier (e.g. "C0001"). Empty/None/"nan" means absent.
        block_suffix: SR1A BLOCK-SUFFIX (4 chars). Used when reconstructing
            PAMS_PIN from SR1A records — joined as "{block}.{suffix}".
        lot_suffix: Same as block_suffix but for lot.

    Returns:
        e.g. "1314_77.01_80.02"  or  "1314_3_33"  or  "1314_3_33_C0001"
    """
    m = str(muni_code).strip()
    b = _join_suffix(str(block), block_suffix)
    l = _join_suffix(str(lot), lot_suffix)
    q = (qualifier or "").strip() if qualifier is not None else ""
    if q.lower() in {"none", "nan"}:
        q = ""
    if q:
        return f"{m}_{b}_{l}_{q}"
    return f"{m}_{b}_{l}"


def parse_pams_pin(pin: str) -> tuple[str, str, str, str]:
    """Inverse of build_pams_pin. Returns (muni_code, block, lot, qualifier).

    qualifier is "" when the PIN has no qualifier component.
    """
    parts = pin.split("_")
    if len(parts) == 3:
        return parts[0], parts[1], parts[2], ""
    if len(parts) == 4:
        return parts[0], parts[1], parts[2], parts[3]
    raise ValueError(f"invalid pams_pin: {pin!r} (expected 3 or 4 parts)")
