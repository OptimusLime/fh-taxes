"""PAMS_PIN construction. The join key across NJGIN and SR1A.

Format: f"{district}_{block}_{lot}_{qualifier}" with qualifier="" when absent.
district zero-padded to 2 chars; block/lot preserved as string (leading zeros
and letter suffixes are meaningful in MOD-IV).
"""
from __future__ import annotations


def build_pams_pin(district, block, lot, qualifier=None) -> str:
    """Build a canonical PAMS_PIN string.

    Args:
        district: District code (will be zfill(2)'d).
        block: MOD-IV block (string preserved verbatim, including letter suffixes).
        lot: MOD-IV lot.
        qualifier: MOD-IV qualifier or None / empty / "nan".

    Returns:
        f"{district:02}_{block}_{lot}_{qualifier_or_empty}"
    """
    d = str(district).strip().zfill(2)
    b = str(block).strip()
    l = str(lot).strip()
    q = (qualifier or "").strip() if qualifier is not None else ""
    if q.lower() in {"none", "nan"}:
        q = ""
    return f"{d}_{b}_{l}_{q}"


def parse_pams_pin(pin: str) -> tuple[str, str, str, str]:
    """Inverse of build_pams_pin. Raises ValueError if input has != 4 parts."""
    parts = pin.split("_")
    if len(parts) != 4:
        raise ValueError(f"invalid pams_pin: {pin!r} (expected 4 parts)")
    return parts[0], parts[1], parts[2], parts[3]
