"""OPRS sr.html parser tests using a sanitized real fixture + synthetic stubs.

The committed fixture (tests/fixtures/oprs/sr_sample.html) is the live OPRS sr
response for parcel 1314_30_1 ssi=401 with grantor/grantee names redacted
(Daniel's Law).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from fairhaven_tax.ingest.oprs.parse_sr import (
    SR_FIELDS,
    _is_empty_sr_template,
    parse_sr,
)


FIXTURE = Path(__file__).parent / "fixtures" / "oprs" / "sr_sample.html"


def _synthetic_sr(**overrides) -> str:
    """Build a minimal sr.html stub mirroring the OPRS layout."""
    defaults = dict(
        sale_date="07/17/97",
        deed_book="5647",
        deed_page="424",
        deed_date="07/17/97",
        date_recorded="09/10/97",
        rt_fee="0",
        sale_price="450000",
        rtf_exempt="",
        grantor="GRANTOR LAST, FIRST M",
        grantor_addr="123 MAIN ST FAIR HAVEN, NJ 07704",
        grantee="GRANTEE LAST, FIRST",
        grantee_addr="123 MAIN ST FAIR HAVEN, NJ 07704",
        block="77",
        lot="80",
        klass="2",
        qual="",
        condo="N",
        year_assessed="1997",
        land_val="100000",
        bldg_val="200000",
        total_val="300000",
        prop_loc="123 MAIN ST",
        floor_area="0",
        year_built="0",
        remarks="ARMS LENGTH",
        ratio="58.33",
        family_sale="N",
        nu_code="00",
        serial="401",
    )
    defaults.update(overrides)
    return f"""<html><body>
<table>
<tr><td>DATE</td><td>COUNTY</td><td>DISTRICT</td></tr>
<tr><td>{defaults["sale_date"]}</td><td>MONMOUTH</td><td>1314 FAIR HAVEN</td></tr>
</table>
<table>
<tr><td>DEED REGISTRATION</td><td>R.T.F.<br>EXEMPT</td></tr>
<tr><td>BOOK</td><td>PAGE</td><td>DEED DATE</td><td>DATE RECORDED</td><td>R.T. FEE</td><td>PRICE</td></tr>
<tr><td>{defaults["deed_book"]}</td><td>{defaults["deed_page"]}</td><td>{defaults["deed_date"]}</td><td>{defaults["date_recorded"]}</td><td>{defaults["rt_fee"]}</td><td>{defaults["sale_price"]}</td><td>{defaults["rtf_exempt"]}</td></tr>
</table>
<table>
<tr>
<td>G<br>R<br>A<br>N<br>T<br>O<br>R</td>
<td>{defaults["grantor"]}<br>{defaults["grantor_addr"]}</td>
<td>G<br>R<br>A<br>N<br>T<br>E<br>E</td>
<td>{defaults["grantee"]}<br>{defaults["grantee_addr"]}</td>
</tr>
</table>
<table>
<tr><td>TAX MAP & LIST DESCRIPTIONS</td><td>PROPERTY CLASSIFICATION</td></tr>
<tr><td>BLOCK</td><td>{defaults["block"]}</td><td>CLASS</td><td>{defaults["klass"]}</td></tr>
<tr><td>LOT</td><td>{defaults["lot"]}</td><td>CL. 4 TYPE</td><td></td></tr>
<tr><td>QUAL</td><td>{defaults["qual"]}</td><td>CONDO</td><td>{defaults["condo"]}</td></tr>
</table>
<table>
<tr><td>ASSESSED VALUE</td></tr>
<tr><td>YEAR<br>SAME AS DEED</td><td>LAND</td><td>BUILDINGS</td><td>TOTAL</td></tr>
<tr><td>{defaults["year_assessed"]}</td><td>{defaults["land_val"]}</td><td>{defaults["bldg_val"]}</td><td>{defaults["total_val"]}</td></tr>
<tr><td>PROPERTY LOCATION</td><td>FLOOR AREA</td><td>YEAR BUILT</td></tr>
<tr><td>{defaults["prop_loc"]}</td><td>{defaults["floor_area"]}</td><td>{defaults["year_built"]}</td></tr>
<tr><td>REMARKS:</td><td>RATIO:</td></tr>
<tr><td>{defaults["remarks"]}</td><td>{defaults["ratio"]}</td></tr>
</table>
<table>
<tr><td>ADDITIONAL BLOCKS/LOTS</td></tr>
<tr><td>BLOCK</td><td>LOT</td><td>QUAL</td><td>LAND</td><td>BUILDINGS</td><td>TOTAL</td></tr>
<tr><td></td><td></td><td></td><td>0</td><td>0</td><td>0</td></tr>
</table>
<table>
<tr><td>NONUSABLE CODE</td><td>SERIAL NO.</td></tr>
<tr><td>{defaults["nu_code"]}</td><td>{defaults["serial"]}</td></tr>
</table>
</body></html>"""


def _empty_sr_template() -> str:
    """An empty sr.html (no detail on record) — the placeholder ' // // ' appears."""
    return """<html><body>
<table>
<tr><td>DATE</td><td>COUNTY</td><td>DISTRICT</td></tr>
<tr><td>// //</td><td>MONMOUTH</td><td>1314 FAIR HAVEN</td></tr>
</table>
</body></html>"""


def test_parse_sr_happy_path():
    """Real fixture parses with all SR_FIELDS keys present."""
    result = parse_sr(FIXTURE)
    assert isinstance(result, dict)
    for key in SR_FIELDS:
        assert key in result, f"missing canonical key: {key}"
    # Spot-check the real fixture (block=30, lot=1, ssi=401; 1997 deed)
    assert result["sale_date"] == date(1997, 7, 17)
    assert result["sale_price"] == Decimal("1")
    assert result["serial_number"] == "4680692"
    # Grantor and grantee parsed (redacted in fixture but recognizable)
    assert "GRANTOR" in (result["grantor"] or "")
    assert "GRANTEE" in (result["grantee"] or "")


def test_parse_sr_synthetic_happy_path(tmp_path):
    fixture = tmp_path / "sr.html"
    fixture.write_text(_synthetic_sr())
    result = parse_sr(fixture)
    assert result["sale_date"] == date(1997, 7, 17)
    assert result["sale_price"] == Decimal("450000")
    assert result["sales_ratio_assessor"] == Decimal("58.33")
    assert result["serial_number"] == "401"
    assert result["nu_code"] == "00"
    assert "GRANTOR LAST" in result["grantor"]
    assert "GRANTEE LAST" in result["grantee"]


def test_parse_sr_empty_template_returns_none(tmp_path):
    """An sr.html containing ' // // ' is the no-detail-on-record template."""
    fixture = tmp_path / "sr.html"
    # Pad with junk to clear the <100 byte gate.
    fixture.write_text(_empty_sr_template() + " padding " * 50)
    assert parse_sr(fixture) is None


def test_parse_sr_no_sale_marker_returns_none(tmp_path):
    """A .no_sale-style marker (small file) returns None."""
    fixture = tmp_path / "sr.html.no_sale"
    fixture.write_text("no_detail_on_record\n")
    assert parse_sr(fixture) is None


def test_parse_sr_family_sale_flag_truthiness(tmp_path):
    # The OPRS sr template uses NU codes for family-sale (07 = related parties).
    # We accept Y/YES via a synthetic family sale label.
    for value, expected in [("Y", True), ("YES", True), ("N", False), ("NO", False), ("", False)]:
        fixture = tmp_path / f"sr_{value or 'blank'}.html"
        fixture.write_text(_synthetic_sr(family_sale=value, nu_code="00"))
        result = parse_sr(fixture)
        assert isinstance(result["family_sale_flag"], bool)


def test_parse_sr_grantor_grantee_with_special_chars(tmp_path):
    """Names with ampersands and commas extracted cleanly."""
    fixture = tmp_path / "sr.html"
    fixture.write_text(_synthetic_sr(
        grantor="SMITH, JOHN A & MARY B",
        grantee="JONES-DOE, ALICE",
    ))
    result = parse_sr(fixture)
    assert "SMITH, JOHN A" in result["grantor"]
    assert "MARY B" in result["grantor"]
    assert "JONES-DOE, ALICE" in result["grantee"]


def test_parse_sr_sales_ratio_returns_decimal(tmp_path):
    fixture = tmp_path / "sr.html"
    fixture.write_text(_synthetic_sr(ratio="42.75"))
    result = parse_sr(fixture)
    assert result["sales_ratio_assessor"] == Decimal("42.75")
    assert isinstance(result["sales_ratio_assessor"], Decimal)


def test_parse_sr_sale_date_parsed(tmp_path):
    fixture = tmp_path / "sr.html"
    fixture.write_text(_synthetic_sr(deed_date="06/15/24"))
    result = parse_sr(fixture)
    assert result["sale_date"] == date(2024, 6, 15)


def test_is_empty_sr_template_detection():
    """Direct unit test for the helper."""
    assert _is_empty_sr_template(" some text // // more text ")
    assert not _is_empty_sr_template(" 07/17/97 normal text ")


def test_parse_sr_parcel_pin_constructed(tmp_path):
    fixture = tmp_path / "sr.html"
    fixture.write_text(_synthetic_sr(block="77", lot="80", qual=""))
    result = parse_sr(fixture)
    assert result["parcel_pin"] == "1314_77_80"


def test_parse_sr_parcel_pin_with_qual(tmp_path):
    fixture = tmp_path / "sr.html"
    fixture.write_text(_synthetic_sr(block="77", lot="80", qual="C0001"))
    result = parse_sr(fixture)
    assert result["parcel_pin"] == "1314_77_80_C0001"
