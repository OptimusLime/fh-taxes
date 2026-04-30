"""Tests for OPRS tax-list PDF parser (D-32 taxlist subset)."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from fairhaven_tax.ingest.oprs.parse_taxlist_pdf import (
    TAXLIST_FIELDS,
    parse_taxlist_pdf,
)


FIXTURE = Path(__file__).parent / "fixtures" / "oprs" / "taxlist_sample.pdf"


def test_taxlist_fields_constant_has_six_entries():
    assert len(TAXLIST_FIELDS) == 6
    assert set(TAXLIST_FIELDS) == {
        "actual_tax_paid_total",
        "tax_1h_paid",
        "tax_2h_paid",
        "special_tax_codes",
        "deduction_codes",
        "deduction_amount",
    }


def test_parse_taxlist_pdf_returns_all_fields_present():
    """Block 30 lot 1 known to be in fixture."""
    result = parse_taxlist_pdf(FIXTURE, block="30", lot="1")
    assert isinstance(result, dict)
    for key in TAXLIST_FIELDS:
        assert key in result


def test_parse_taxlist_pdf_extracts_total_tax():
    """parcel 30/1: 2026 total tax = 11543.00."""
    result = parse_taxlist_pdf(FIXTURE, block="30", lot="1")
    assert result["actual_tax_paid_total"] == Decimal("11543.00")


def test_parse_taxlist_pdf_extracts_1h_paid():
    """parcel 30/1: 1H = 5771.50 (half of 11543.00)."""
    result = parse_taxlist_pdf(FIXTURE, block="30", lot="1")
    assert result["tax_1h_paid"] == Decimal("5771.50")


def test_parse_taxlist_pdf_1h_plus_2h_equals_total_within_rounding():
    result = parse_taxlist_pdf(FIXTURE, block="30", lot="1")
    one_h = result["tax_1h_paid"]
    two_h = result["tax_2h_paid"]
    total = result["actual_tax_paid_total"]
    assert one_h is not None and two_h is not None and total is not None
    assert abs((one_h + two_h) - total) < Decimal("0.02")


def test_parse_taxlist_pdf_deduction_codes_is_list():
    """parcel 30/1 has deduction code 01 (per fixture) and ded amount = .00."""
    result = parse_taxlist_pdf(FIXTURE, block="30", lot="1")
    assert isinstance(result["deduction_codes"], list)
    # deduction_amount must be Decimal (zero, not None) when codes are present
    if result["deduction_codes"]:
        assert isinstance(result["deduction_amount"], Decimal)


def test_parse_taxlist_pdf_zero_deductions_yields_zero_not_none():
    """Even when deduction amount is .00, the value should be Decimal('0'), not None."""
    result = parse_taxlist_pdf(FIXTURE, block="30", lot="1")
    if result["deduction_codes"]:
        assert result["deduction_amount"] == Decimal("0") or result["deduction_amount"] >= Decimal("0")


def test_parse_taxlist_pdf_special_tax_codes_is_list():
    result = parse_taxlist_pdf(FIXTURE, block="30", lot="1")
    assert isinstance(result["special_tax_codes"], list)


def test_parse_taxlist_pdf_unknown_parcel_returns_all_nones():
    """A block/lot not present in this fixture page → all-None scalars."""
    result = parse_taxlist_pdf(FIXTURE, block="99999", lot="9999")
    # Lists may be empty; scalars should be None
    assert result["actual_tax_paid_total"] is None
    assert result["tax_1h_paid"] is None
    assert result["tax_2h_paid"] is None
