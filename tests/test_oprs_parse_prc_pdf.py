"""Tests for OPRS PRC PDF parser (D-32 PRC subset, 30 fields)."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from fairhaven_tax.ingest.oprs.parse_prc_pdf import (
    PRC_PDF_FIELDS,
    parse_prc_pdf,
)


FIXTURE = Path(__file__).parent / "fixtures" / "oprs" / "prc_sample.pdf"


def test_prc_pdf_fields_constant_has_thirty_entries():
    assert len(PRC_PDF_FIELDS) == 30
    assert len(set(PRC_PDF_FIELDS)) == 30  # no duplicates


def test_parse_prc_pdf_returns_dict_with_all_fields():
    """Every key in PRC_PDF_FIELDS must appear in result, even if value is None."""
    result = parse_prc_pdf(FIXTURE)
    assert isinstance(result, dict)
    for key in PRC_PDF_FIELDS:
        assert key in result, f"missing key: {key}"


def test_parse_prc_pdf_extracts_bedrooms_as_int():
    result = parse_prc_pdf(FIXTURE)
    # parcel 30/1 has Bed: 3
    assert result["bedrooms"] == 3
    assert isinstance(result["bedrooms"], int)


def test_parse_prc_pdf_extracts_bathrooms_as_int():
    result = parse_prc_pdf(FIXTURE)
    # parcel 30/1 has Bth: 2
    assert result["bathrooms"] == 2
    assert isinstance(result["bathrooms"], int)


def test_parse_prc_pdf_extracts_room_count():
    result = parse_prc_pdf(FIXTURE)
    # parcel 30/1 has Tot: 7
    assert result["room_count"] == 7


def test_parse_prc_pdf_livable_area_is_decimal():
    result = parse_prc_pdf(FIXTURE)
    # parcel 30/1 has Livable Area: 1763
    assert result["livable_area"] == Decimal("1763")
    assert isinstance(result["livable_area"], Decimal)


def test_parse_prc_pdf_eff_age_is_int():
    result = parse_prc_pdf(FIXTURE)
    # parcel 30/1 has Eff Age (Years): 30
    assert result["eff_age"] == 30


def test_parse_prc_pdf_condition_uppercase_string():
    result = parse_prc_pdf(FIXTURE)
    # parcel 30/1 has Condition: NORMAL
    assert result["condition"] == "NORMAL"
    assert result["condition"] == result["condition"].upper()


def test_parse_prc_pdf_extracts_foundation():
    result = parse_prc_pdf(FIXTURE)
    # parcel 30/1 has Foundation: CONCRETE BLOCK
    assert result["foundation"] == "CONCRETE BLOCK"


def test_parse_prc_pdf_extracts_roof_type():
    result = parse_prc_pdf(FIXTURE)
    assert result["roof_type"] == "GABLE"


def test_parse_prc_pdf_extracts_roof_material():
    result = parse_prc_pdf(FIXTURE)
    assert result["roof_material"] == "SHINGLE"


def test_parse_prc_pdf_extracts_exterior():
    result = parse_prc_pdf(FIXTURE)
    assert result["exterior"] == "FRAME"


def test_parse_prc_pdf_extracts_story_breakdown_decimals():
    result = parse_prc_pdf(FIXTURE)
    assert result["first_story_sf"] == Decimal("986")
    assert result["upper_story_sf"] == Decimal("756")
    assert result["half_story_sf"] == Decimal("36")


def test_parse_prc_pdf_extracts_fireplaces():
    result = parse_prc_pdf(FIXTURE)
    # parcel 30/1: FIREPLACE 2STY 1
    assert result["fireplaces"] == 1


def test_parse_prc_pdf_extracts_heating():
    result = parse_prc_pdf(FIXTURE)
    # FORCED HOT AIR 1763 SF
    assert "FORCED HOT AIR" in (result["heating_type"] or "")
    assert result["heating_sf"] == Decimal("1763")


def test_parse_prc_pdf_extracts_ac():
    result = parse_prc_pdf(FIXTURE)
    assert result["ac_type"] is not None
    assert "COMB DUCTS" in result["ac_type"] or "AC" in result["ac_type"]
    assert result["ac_sf"] == Decimal("1763")


def test_parse_prc_pdf_extracts_topography_and_road():
    result = parse_prc_pdf(FIXTURE)
    assert result["topography"] == "LEVEL"
    assert result["road_type"] == "PAVED"


def test_parse_prc_pdf_corrupt_pdf_raises_or_returns_nones(tmp_path):
    """Garbled PDF should either raise ValueError or return all-None dict (graceful)."""
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4\n%not a real pdf\n%%EOF")
    try:
        result = parse_prc_pdf(bad)
    except (ValueError, Exception):
        return  # acceptable per <behavior> contract
    # If it returns a dict, all values should be None (no data extracted)
    assert isinstance(result, dict)
    for key in PRC_PDF_FIELDS:
        assert result[key] is None, f"unexpected value for {key}: {result[key]}"
