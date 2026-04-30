"""Parse OPRS Chapter 75 annual notice PDF → 4-field dict (D-32 ch75 subset).

The Chapter 75 notice is an N.J.S.A. 54:4-38.1 mailing showing the prior-year
and current-year assessments side by side. We extract:

    prior_year_assessment   — last year's net total assessment (Decimal)
    current_year_assessment — this year's net total assessment (Decimal)
    assessment_change_pct   — (curr - prior) / prior * 100  (Decimal)
    notice_year             — the assessment year (int, e.g. 2026)

ch75 PDFs are produced by an upstream Apache that omits the /Page MediaBox,
so pdfplumber raises during page initialization. We fall back to pdfminer.six
(pdfplumber's underlying engine) which handles missing MediaBox by defaulting
to US Letter — see datasets/collect_oprs.py::_pdfplumber_page1_ok for the
canonical fallback recipe.

The text extraction yields whitespace-tabular content rather than labeled
rows; we anchor on the three-amount land/improvement/total line.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber

CH75_FIELDS = [
    "prior_year_assessment",
    "current_year_assessment",
    "assessment_change_pct",
    "notice_year",
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
    """ch75.cgi PDFs miss MediaBox → pdfplumber raises; pdfminer.six handles it."""
    try:
        with pdfplumber.open(str(path)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        joined = "\n".join(pages)
        if joined.strip():
            return joined
    except Exception:
        pass
    try:
        from pdfminer.high_level import extract_text

        return extract_text(str(path)) or ""
    except Exception:
        return ""


# Three large comma-separated numbers on one line — land, improvement, total
# (D-32: current_year_assessment is the third / "Total" column).
_THREE_AMOUNTS_RE = re.compile(
    r"^\s*([\d]{1,3}(?:,\d{3})+)\s+([\d]{1,3}(?:,\d{3})+)\s+([\d]{1,3}(?:,\d{3})+)\s*$",
    re.M,
)
# A single comma-separated amount on its own line (used for prior-year total).
_LONE_AMOUNT_RE = re.compile(
    r"^\s*([\d]{1,3}(?:,\d{3})+)\s*$",
    re.M,
)
# Notice year — first standalone 4-digit year >= 2000 in the document.
_YEAR_RE = re.compile(r"\b(20\d{2})\b")


def parse_ch75_pdf(path: Path) -> dict[str, object]:
    """Parse one ch75.pdf → 4-field dict (D-32).

    Returns a dict with all CH75_FIELDS keys; values are Decimal/int or None
    when the field cannot be located. The assessment_change_pct is computed
    as (current - prior) / prior * 100 when both anchors are present.
    """
    path = Path(path)
    text = _extract_text(path)
    result: dict[str, object] = {k: None for k in CH75_FIELDS}
    if not text.strip():
        return result

    # Locate the land/improvement/total line. The first such line is the
    # canonical "current year" row. The PDF may have multiple three-amount
    # rows (e.g. assessor mailing data), but the legal notice form has
    # exactly one.
    m = _THREE_AMOUNTS_RE.search(text)
    if m:
        # Group 3 = total (the net taxable value column).
        result["current_year_assessment"] = _to_decimal(m.group(3))

        # Prior-year total appears as a standalone amount BELOW the
        # land/improvement/total row, after a "2025" / "2024" reference line.
        tail = text[m.end() :]
        prior = None
        for lone in _LONE_AMOUNT_RE.finditer(tail):
            candidate = _to_decimal(lone.group(1))
            # Skip dollar amounts that look like tax bills (e.g. $11,543.00 is
            # filtered by _LONE_AMOUNT_RE having no decimal anyway, but be
            # defensive: the prior-year assessment should be a "round-ish"
            # value, typically of similar magnitude to current.
            if candidate is None:
                continue
            curr = result["current_year_assessment"]
            if isinstance(curr, Decimal) and candidate < curr / Decimal("10"):
                # Too small to be the prior assessment.
                continue
            prior = candidate
            break
        result["prior_year_assessment"] = prior

    # Notice year — first 20xx token in document (e.g. "2026").
    ym = _YEAR_RE.search(text)
    if ym:
        result["notice_year"] = _to_int(ym.group(1))

    # Computed assessment_change_pct.
    prior = result["prior_year_assessment"]
    curr = result["current_year_assessment"]
    if isinstance(prior, Decimal) and isinstance(curr, Decimal) and prior != 0:
        result["assessment_change_pct"] = (curr - prior) / prior * Decimal("100")

    return result
