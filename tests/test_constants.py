"""Tests for project-wide constants."""
from decimal import Decimal

from fairhaven_tax import constants


def test_mun_code():
    assert constants.MUN_CODE_FAIR_HAVEN == "1314"
    assert constants.MUN_CODE_FAIR_HAVEN_DLGS == "1313"
    assert constants.SR1A_COUNTY_MONMOUTH == "13"
    assert constants.SR1A_DISTRICT_FAIR_HAVEN == "14"


def test_arms_length_nu_codes():
    """Per NJ DOT convention, blank NU code is the arms-length signal."""
    expected = frozenset({"", "0", "00"})
    assert constants.ARMS_LENGTH_NU_CODES == expected
    for nu in ("01", "07", "10", "26", "27", "33"):
        assert nu not in constants.ARMS_LENGTH_NU_CODES


def test_crs_constants():
    assert constants.CRS_NATIVE == "EPSG:3424"
    assert constants.CRS_EXPORT == "EPSG:4326"


def test_validation_tolerance():
    assert constants.VALIDATION_TOLERANCE == Decimal("0.05")
    assert constants.EXPECTED_PARCEL_COUNT == 2064
    assert constants.EXPECTED_AGGREGATE_ASSESSED == Decimal("2_740_871_000")
