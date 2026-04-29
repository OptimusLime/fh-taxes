"""Tests for PAMS_PIN constructor (NJGIN canonical format)."""
import pytest

from fairhaven_tax.ingest.pams_pin import build_pams_pin, parse_pams_pin


def test_build_basic():
    """No qualifier → 3 parts, no trailing underscore (matches real NJGIN)."""
    assert build_pams_pin("1314", "101", "5") == "1314_101_5"


def test_build_strips_leading_zeros():
    """SR1A ships block/lot zero-padded to 5 chars; output strips them."""
    assert build_pams_pin("1314", "00077", "00080") == "1314_77_80"


def test_build_with_qualifier():
    assert build_pams_pin("1314", "3", "33", "C0001") == "1314_3_33_C0001"


def test_build_with_block_suffix():
    """SR1A BLOCK_SUFFIX='01' → 'block.01'."""
    assert build_pams_pin("1314", "00077", "00001", block_suffix="01") == "1314_77.01_1"


def test_build_with_lot_suffix():
    """SR1A LOT_SUFFIX='02' → 'lot.02'."""
    assert build_pams_pin("1314", "00077", "00080", lot_suffix="02") == "1314_77_80.02"


def test_build_pads_short_suffix_to_2_digits():
    """SR1A right-justifies suffix in 4-char field; '1' → '.01' to match NJGIN."""
    assert build_pams_pin("1314", "00027", "00032", lot_suffix="1") == "1314_27_32.01"


def test_build_preserves_decimal_lots():
    """NJGIN already uses decimal lots like '15.01'; pass through unchanged."""
    assert build_pams_pin("1314", "30", "15.01") == "1314_30_15.01"


def test_roundtrip_3_parts():
    pin = build_pams_pin("1314", "3", "33")
    m, b, l, q = parse_pams_pin(pin)
    assert (m, b, l, q) == ("1314", "3", "33", "")


def test_roundtrip_4_parts():
    pin = build_pams_pin("1314", "3", "33", "C0001")
    m, b, l, q = parse_pams_pin(pin)
    assert (m, b, l, q) == ("1314", "3", "33", "C0001")


def test_parse_invalid_too_few():
    with pytest.raises(ValueError):
        parse_pams_pin("only_two")


def test_parse_invalid_too_many():
    with pytest.raises(ValueError):
        parse_pams_pin("a_b_c_d_e")


def test_nan_qualifier_drops_to_3_parts():
    assert build_pams_pin("1314", "3", "33", "nan") == "1314_3_33"
    assert build_pams_pin("1314", "3", "33", "NaN") == "1314_3_33"
    assert build_pams_pin("1314", "3", "33", "None") == "1314_3_33"
    assert build_pams_pin("1314", "3", "33", "") == "1314_3_33"
