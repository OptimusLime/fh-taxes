from decimal import Decimal
from fairhaven_tax import constants


def test_mun_code() -> None:
    assert constants.MUN_CODE_FAIR_HAVEN == "1314"


def test_arms_length_nu_codes() -> None:
    # Per D-12 / DATA-03: only these NU codes survive the arms-length filter
    assert constants.SR1A_ARMS_LENGTH_NU_CODES == frozenset({"0", "07", "10", "26", "33"})


def test_crs_constants() -> None:
    assert constants.CRS_NATIVE == "EPSG:3424"
    assert constants.CRS_EXPORT == "EPSG:4326"


def test_validation_tolerance() -> None:
    assert constants.VALIDATION_TOLERANCE == Decimal("0.05")
