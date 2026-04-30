"""OPRS m4.html parser tests using a sanitized real fixture + synthetic stubs.

The committed fixture (tests/fixtures/oprs/m4_sample.html) is the live OPRS m4
response for parcel 1314_30_1 with owner names redacted (Daniel's Law). For
edge cases we build synthetic minimal HTML inline.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from fairhaven_tax.ingest.oprs.parse_m4 import (
    M4_FIELDS,
    extract_ssis,
    parse_m4,
)


FIXTURE = Path(__file__).parent / "fixtures" / "oprs" / "m4_sample.html"


def _synthetic_m4(**overrides) -> str:
    """Build a minimal m4.html stub mirroring the OPRS layout.

    Defaults match the real Fair Haven layout (label cell + value cell pairs).
    """
    defaults = dict(
        block="77",
        lot="80",
        qual="",
        prop_loc="123 MAIN ST",
        owner="REDACTED OWNER",
        square_ft="2500",
        year_built="2010",
        style="5",
        bldg_desc="2S-AL-O-1U",
        land_desc="50X100",
        class_="2",
        zone="R-5",
        map_page="6",
        acreage="0.25",
        taxes="11543.00 / 0.00",
        updated="10/09/23",
    )
    defaults.update(overrides)
    return f"""<html><body>
<table>
<tr>
<td><font color=BLACK>Block: </font></td>
<td><font color=FIREBRICK>{defaults["block"]} </font></td>
<td><font color=BLACK>Prop Loc: </font></td>
<td><font color=FIREBRICK>{defaults["prop_loc"]} </font></td>
<td><font color=BLACK>Owner: </font></td>
<td><font color=FIREBRICK>{defaults["owner"]} </font></td>
<td><font color=BLACK>Square Ft: </font></td>
<td><font color=FIREBRICK>{defaults["square_ft"]} </font></td>
</tr>
<tr>
<td><font color=BLACK>Lot: </font></td>
<td><font color=FIREBRICK>{defaults["lot"]}   </font></td>
<td><font color=BLACK>District: </font></td>
<td><font color=FIREBRICK>1314 FAIR HAVEN &nbsp</font></td>
<td><font color=BLACK>Street: </font></td>
<td><font color=FIREBRICK>FAKE STREET </font></td>
<td><font color=BLACK>Year Built: </font></td>
<td><font color=FIREBRICK>{defaults["year_built"]} </font></td>
</tr>
<tr>
<td><font color=BLACK>Qual: </font></td>
<td><font color=FIREBRICK> {defaults["qual"]}</font></td>
<td><font color=BLACK>Class: </font></td>
<td><font color=FIREBRICK>{defaults["class_"]} </font></td>
<td><font color=BLACK>City State: </font></td>
<td><font color=FIREBRICK>FAIR HAVEN, NJ 07704 </font></td>
<td><font color=BLACK>Style: </font></td>
<td><font color=FIREBRICK>{defaults["style"]} </font></td>
</tr>
<tr>
<td><font color=BLACK>Land Desc: </font></td>
<td><font color=FIREBRICK>{defaults["land_desc"]} </font></td>
<td><font color=BLACK>Bldg Desc: </font></td>
<td><font color=FIREBRICK>{defaults["bldg_desc"]} </font></td>
</tr>
<tr>
<td><font color=BLACK>Updated: </font></td>
<td><font color=FIREBRICK>{defaults["updated"]} &nbsp&nbsp </font></td>
</tr>
<tr>
<td><font color=BLACK>Zone: </font></td>
<td><font color=FIREBRICK>{defaults["zone"]} </font></td>
<td><font color=BLACK>Map Page: </font></td>
<td><font color=FIREBRICK>{defaults["map_page"]} </font></td>
<td><font color=BLACK>Acreage: </font></td>
<td><font color=FIREBRICK>{defaults["acreage"]} </font></td>
<td><font color=BLACK>Taxes: </font></td>
<td><font color=FIREBRICK>{defaults["taxes"]} </font></td>
</tr>
</table>
</body></html>"""


def test_parse_m4_happy_path(tmp_path):
    """Real fixture parses with all M4_FIELDS keys present."""
    result = parse_m4(FIXTURE)
    assert isinstance(result, dict)
    # Every canonical field must be a key (None or value)
    for key in M4_FIELDS:
        assert key in result, f"missing canonical key: {key}"
    # Spot-check known values from the real fixture (block=30, lot=1, no qual)
    assert result["block"] == "30"
    assert result["lot"] == "1"
    assert result["qualifier"] is None or result["qualifier"] == ""
    assert result["pams_pin"] == "1314_30_1"
    assert result["year_built"] == 1912
    assert result["square_ft"] == 1763
    assert result["zone"] == "R-5"
    assert result["map_page"] == "6"
    assert result["class"] == "2"
    assert result["bldg_desc"] == "2S-AL-O-1U"
    assert result["land_desc"] == "35X160IRR"
    assert result["current_taxes_1h"] == Decimal("11543.00")
    assert result["current_taxes_2h"] == Decimal("0.00")


def test_parse_m4_synthetic_minimal(tmp_path):
    """Synthetic stub: every canonical field populated."""
    fixture = tmp_path / "m4.html"
    fixture.write_text(_synthetic_m4())
    result = parse_m4(fixture)
    assert result["block"] == "77"
    assert result["lot"] == "80"
    assert result["pams_pin"] == "1314_77_80"
    assert result["year_built"] == 2010
    assert result["square_ft"] == 2500
    assert result["acreage"] == Decimal("0.25")
    assert result["zone"] == "R-5"
    assert result["bldg_desc"] == "2S-AL-O-1U"
    assert result["class"] == "2"
    assert result["style_code"] == "5"


def test_parse_m4_missing_year_built_returns_none(tmp_path):
    """Missing optional field surfaces as None, not a raise."""
    fixture = tmp_path / "m4.html"
    fixture.write_text(_synthetic_m4(year_built=""))
    result = parse_m4(fixture)
    assert result["year_built"] is None


def test_parse_m4_qualifier_absent_yields_3part_pams_pin(tmp_path):
    fixture = tmp_path / "m4.html"
    fixture.write_text(_synthetic_m4(qual=""))
    result = parse_m4(fixture)
    assert result["pams_pin"] == "1314_77_80"


def test_parse_m4_qualifier_present_yields_4part_pams_pin(tmp_path):
    fixture = tmp_path / "m4.html"
    fixture.write_text(_synthetic_m4(qual="C0001"))
    result = parse_m4(fixture)
    assert result["pams_pin"] == "1314_77_80_C0001"
    assert result["qualifier"] == "C0001"


def test_parse_m4_decimal_acreage(tmp_path):
    fixture = tmp_path / "m4.html"
    fixture.write_text(_synthetic_m4(acreage="1.234"))
    result = parse_m4(fixture)
    assert result["acreage"] == Decimal("1.234")


def test_parse_m4_money_with_dollar_signs_and_commas(tmp_path):
    """Tax field uses '11,543.00 / $1,000.50' style — coercer strips $/, ."""
    fixture = tmp_path / "m4.html"
    fixture.write_text(_synthetic_m4(taxes="$11,543.00 / $1,000.50"))
    result = parse_m4(fixture)
    assert result["current_taxes_1h"] == Decimal("11543.00")
    assert result["current_taxes_2h"] == Decimal("1000.50")


def test_parse_m4_html_entities_normalized(tmp_path):
    """&nbsp; and &amp; do not leak into extracted values."""
    fixture = tmp_path / "m4.html"
    fixture.write_text(_synthetic_m4(zone="R-5&nbsp;"))
    result = parse_m4(fixture)
    # The flatten step turns &nbsp; into a space — extracted zone should not contain it
    assert "&nbsp;" not in (result["zone"] or "")
    assert "&" not in (result["zone"] or "")


def test_parse_m4_updated_date_parsed(tmp_path):
    """Updated date '10/09/23' → date(2023, 10, 9)."""
    fixture = tmp_path / "m4.html"
    fixture.write_text(_synthetic_m4(updated="10/09/23"))
    result = parse_m4(fixture)
    from datetime import date
    assert result["updated_date"] == date(2023, 10, 9)


def test_parse_m4_bad_numeric_returns_none(tmp_path):
    """A non-numeric square_ft yields None, not a raise."""
    fixture = tmp_path / "m4.html"
    fixture.write_text(_synthetic_m4(square_ft="N/A"))
    result = parse_m4(fixture)
    assert result["square_ft"] is None


def test_extract_ssis_dedup_preserves_order():
    """ssi enumeration: dedup, document order preserved."""
    html = (
        '<a href="sr.cgi?&district=1314&ms_user=&ssi=401&block=30&lot=1&qual=">More</a>'
        '<a href="sr.cgi?&district=1314&ms_user=&ssi=1123&block=30&lot=1&qual=">More</a>'
        '<a href="sr.cgi?&district=1314&ms_user=&ssi=1562&block=30&lot=1&qual=">More</a>'
        '<a href="sr.cgi?&district=1314&ms_user=&ssi=401&block=30&lot=1&qual=">Dup</a>'
    )
    ssis = extract_ssis(html)
    assert ssis == ["401", "1123", "1562"]


def test_extract_ssis_real_fixture():
    """The committed real fixture has 3 ssi links."""
    html = FIXTURE.read_text()
    ssis = extract_ssis(html)
    assert ssis == ["401", "1123", "1562"]
