"""Tests for PAMS_PIN constructor."""
import pytest

from fairhaven_tax.ingest.pams_pin import build_pams_pin, parse_pams_pin


def test_build_basic():
    assert build_pams_pin("14", "101", "5", None) == "14_101_5_"


def test_build_pads_district():
    assert build_pams_pin("4", "101", "5", "") == "04_101_5_"


def test_build_with_qualifier():
    assert build_pams_pin("14", "101", "5", "Q0001") == "14_101_5_Q0001"


def test_build_preserves_block_letters():
    assert build_pams_pin("14", "101A", "5.01", None) == "14_101A_5.01_"


def test_roundtrip():
    pin = build_pams_pin("14", "101A", "5.01", "Q1")
    d, b, l, q = parse_pams_pin(pin)
    assert (d, b, l, q) == ("14", "101A", "5.01", "Q1")


def test_parse_invalid():
    with pytest.raises(ValueError):
        parse_pams_pin("only_three_parts")


def test_nan_qualifier():
    assert build_pams_pin("14", "101", "5", "nan") == "14_101_5_"
    assert build_pams_pin("14", "101", "5", "NaN") == "14_101_5_"
    assert build_pams_pin("14", "101", "5", "None") == "14_101_5_"
