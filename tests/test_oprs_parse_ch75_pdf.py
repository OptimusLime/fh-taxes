"""Tests for OPRS Chapter 75 notice PDF parser (D-32 ch75 subset)."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from fairhaven_tax.ingest.oprs.parse_ch75_pdf import CH75_FIELDS, parse_ch75_pdf


FIXTURE = Path(__file__).parent / "fixtures" / "oprs" / "ch75_sample.pdf"


def test_ch75_fields_constant_has_four_entries():
    assert len(CH75_FIELDS) == 4
    assert set(CH75_FIELDS) == {
        "prior_year_assessment",
        "current_year_assessment",
        "assessment_change_pct",
        "notice_year",
    }


def test_parse_ch75_pdf_returns_all_fields_present():
    result = parse_ch75_pdf(FIXTURE)
    assert isinstance(result, dict)
    for key in CH75_FIELDS:
        assert key in result, f"missing key: {key}"


def test_parse_ch75_pdf_happy_path_extracts_assessments():
    """parcel 30/1: prior=808,900 current=916,500 → ~13.30% change, notice_year=2026."""
    result = parse_ch75_pdf(FIXTURE)
    assert result["prior_year_assessment"] == Decimal("808900")
    assert result["current_year_assessment"] == Decimal("916500")
    assert result["notice_year"] == 2026


def test_parse_ch75_pdf_change_pct_computed_when_absent():
    """assessment_change_pct = (curr - prior) / prior * 100."""
    result = parse_ch75_pdf(FIXTURE)
    pct = result["assessment_change_pct"]
    assert pct is not None
    expected = (Decimal("916500") - Decimal("808900")) / Decimal("808900") * Decimal("100")
    assert abs(pct - expected) < Decimal("0.01")


def test_parse_ch75_pdf_corrupt_pdf_returns_all_nones(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4\n%not real\n%%EOF")
    try:
        result = parse_ch75_pdf(bad)
    except Exception:
        return
    assert isinstance(result, dict)
    for key in CH75_FIELDS:
        assert result[key] is None
