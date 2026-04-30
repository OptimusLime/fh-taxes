"""Bloustein MOD-IV historical loader tests using synthetic CSV fixtures.

The fixtures are generated dynamically (in this test module) from the real
132-column Bloustein header so the tests stay calibrated to the production
schema without committing a large checked-in fixture.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from fairhaven_tax.ingest.bloustein import (
    BLOUSTEIN_TO_CANONICAL,
    CANONICAL_HISTORY_COLS,
    parse_bloustein_all,
    parse_bloustein_year,
)


# Real Bloustein header — 132 columns, identical across 1989-2025.
_HEADER = (
    "mod_iv_recordid,mod_iv_year,mun_code_id,mod_iv_county_name,mod_iv_munis_name,"
    "gis_pin,county_district,property_id_blk,property_id_lot,property_id_qualifier,"
    "qualification_code_name,record_id,sub_record_id,last_trans_date_MMDDYY,"
    "last_trans_update_number,tax_acct_number,property_class,property_class_code_name,"
    "property_location,building_description,land_description,calculated_acreage,"
    "additional_lots_1,additional_lots_2,zoning,tax_map_page_number,street_address,"
    "city_state,zip_code,zip_code_plus_four,number_of_owners,deduction_amount,filler,"
    "bank_code,mortgage_account_number,deed_book,deed_page,sales_price_code,"
    "deed_date_MMDDYY,sale_price,sale_assessment,sale_sr1a_non_usable_code,"
    "number_of_dwellings,number_of_commercial_dwell,multiple_occupancy_code,"
    "percentage_owned_code,rebate_code,additional_rebate_code,delquency_code,epl_own,"
    "epl_own_name_of_owner,epl_use,epl_use_name,epl_description,epl_description_name,"
    "initial_date_MMDDYY,further_date_MMDDYY,statute_number,facility_name,"
    "building_class_code,building_class_code_dwelling_type,building_class_code_class,"
    "year_constructed,assessment_code,land_value,improvement_value,net_taxable_value,"
    "sptax_code_1,sptax_code_1_id,sptax_code_1_name,sptax_code_2,sptax_code_2_id,"
    "sptax_code_2_name,sptax_code_3,sptax_code_3_id,sptax_code_3_name,sptax_code_4,"
    "sptax_code_4_id,sptax_code_4_name,exemption_code_1,exemption_amount_1,"
    "exempt_code_1_name,exemption_code_2,exemption_amount_2,exempt_code_2_name,"
    "exemption_code_3,exemption_amount_3,exempt_code_3_name,exemption_code_4,"
    "exemption_amount_4,exempt_code_4_name,senior_citizen_count,veteran_count,"
    "widows_of_veterans_count,surviving_spouse_count,disable_person_count,"
    "user_field_1,user_field_2,old_property_id,old_block,old_lot,old_qualifier,"
    "census_tract,census_block,property_use_code,property_use_code_name,"
    "property_flags,tenant_rebate_response_flg,tenant_rebate_base_year,"
    "tenant_rebate_base_yr_tax,tenant_rebate_base_yr_tax_text,"
    "tenant_rebate_base_yr_net_val,filler_1,last_year_total_tax,current_year_total_tax,"
    "school_tax_overage,taxes_non_municipal_half1,taxes_non_municipal_half1_text,"
    "taxes_non_municipal_half2,taxes_non_municipal_half2_text,taxes_municipal_half1,"
    "taxes_municipal_half1_text,taxes_municipal_half2,taxes_municipal_half2_text,"
    "taxes_non_municipal_half3,taxes_non_municipal_half3_text,taxes_municipal_half3,"
    "taxes_municipal_half3_text,taxes_bill_status_flag,taxes_estimated_qtr3_tax,"
    "prior_year_net_value,statement_of_state_aid_amt"
)
_COLS = _HEADER.split(",")
assert len(_COLS) == 132, f"expected 132 cols, got {len(_COLS)}"


def _row(**overrides) -> str:
    """Build one CSV row matching the 132-col header. Empty default for unspecified."""
    defaults: dict[str, str] = {c: "" for c in _COLS}
    defaults["mun_code_id"] = "234"  # Fair Haven
    defaults["mod_iv_county_name"] = "MONMOUTH"
    defaults["mod_iv_munis_name"] = "Fair Haven Borough"
    defaults["county_district"] = "1314"
    defaults["property_class"] = "2"
    defaults.update({k: str(v) if v is not None else "" for k, v in overrides.items()})
    parts = []
    for c in _COLS:
        v = defaults[c]
        # Quote values containing commas
        if "," in v:
            parts.append(f'"{v}"')
        else:
            parts.append(v)
    return ",".join(parts)


def _write_csv(path: Path, rows: list[dict]) -> Path:
    lines = [_HEADER]
    for r in rows:
        lines.append(_row(**r))
    path.write_text("\n".join(lines) + "\n")
    return path


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def _five_typical_rows() -> list[dict]:
    return [
        # Row 1: typical sale this year — all money fields populated
        dict(
            property_id_blk="77", property_id_lot="80", property_id_qualifier="",
            property_location="100 RIVER RD", building_description="2S-F-R-1U",
            calculated_acreage="0.41320",
            street_address="100 RIVER RD", city_state="FAIR HAVEN, N J",
            land_value="400000", improvement_value="500000", net_taxable_value="900000",
            deduction_amount="0",
            deed_book="09199", deed_page="08259",
            deed_date_MMDDYY="2020-06-15",
            sale_price="1234567",        # tests "1234567" coercion
            sale_assessment="900000",
            sale_sr1a_non_usable_code="",
            year_constructed="1952",
            number_of_dwellings="1",
        ),
        # Row 2: NO sale this year (sale_price/assessment empty)
        dict(
            property_id_blk="77", property_id_lot="81", property_id_qualifier="",
            property_location="102 RIVER RD",
            street_address="102 RIVER RD", city_state="FAIR HAVEN, N J",
            land_value="396600", improvement_value="196500", net_taxable_value="593100",
            deed_book="", deed_page="",
            deed_date_MMDDYY="",
            sale_price="", sale_assessment="",
            year_constructed="1960",
            number_of_dwellings="1",
        ),
        # Row 3: qualifier present (condo unit) — tests 4-part PIN
        dict(
            property_id_blk="3", property_id_lot="33", property_id_qualifier="C0001",
            property_location="50 RIVER RD UNIT 1",
            street_address="50 RIVER RD", city_state="FAIR HAVEN, N J",
            land_value="100000", improvement_value="200000", net_taxable_value="300000",
            year_constructed="1985",
            number_of_dwellings="1",
        ),
        # Row 4: out-of-town (absentee) owner — different city_state
        dict(
            property_id_blk="3", property_id_lot="3.01", property_id_qualifier="",
            property_location="324 HARDING ROAD",
            street_address="29 CIRCLE DRIVE", city_state="RUMSON, NJ",
            land_value="422300", improvement_value="309700", net_taxable_value="732000",
            sale_price="725000", sale_assessment="555800",
            deed_date_MMDDYY="2020-05-21",
            year_constructed="1947",
            number_of_dwellings="1",
        ),
        # Row 5: missing block (should be filtered out — no parcel_pin)
        dict(
            property_id_blk="", property_id_lot="99",
            property_location="MISSING BLOCK",
            land_value="100", improvement_value="200", net_taxable_value="300",
        ),
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_parse_bloustein_year_returns_canonical_cols(tmp_path):
    csv = _write_csv(tmp_path / "mod_iv_2020.csv", _five_typical_rows())
    df = parse_bloustein_year(csv, 2020)
    assert list(df.columns) == CANONICAL_HISTORY_COLS, (
        f"columns drift: got {list(df.columns)} want {CANONICAL_HISTORY_COLS}"
    )


def test_parse_bloustein_year_constructs_3part_parcel_pin(tmp_path):
    csv = _write_csv(tmp_path / "mod_iv_2020.csv", _five_typical_rows())
    df = parse_bloustein_year(csv, 2020)
    pins = set(df["parcel_pin"])
    # Row 1: block 77 lot 80 no qual → 1314_77_80
    assert "1314_77_80" in pins
    # Row 2: block 77 lot 81 → 1314_77_81
    assert "1314_77_81" in pins


def test_parse_bloustein_year_qualifier_yields_4part_pin(tmp_path):
    csv = _write_csv(tmp_path / "mod_iv_2020.csv", _five_typical_rows())
    df = parse_bloustein_year(csv, 2020)
    pins = set(df["parcel_pin"])
    # Row 3: block 3 lot 33 qual C0001 → 1314_3_33_C0001
    assert "1314_3_33_C0001" in pins


def test_parse_bloustein_year_missing_block_is_dropped(tmp_path):
    csv = _write_csv(tmp_path / "mod_iv_2020.csv", _five_typical_rows())
    df = parse_bloustein_year(csv, 2020)
    # Row 5 has no block — must be filtered out
    assert len(df) == 4, f"expected 4 rows after filter, got {len(df)}"
    assert df["parcel_pin"].notna().all()


def test_parse_bloustein_year_money_coercion(tmp_path):
    rows = [
        dict(
            property_id_blk="1", property_id_lot="1",
            land_value="$1,234.56",          # dollar sign + comma
            improvement_value="2000",         # plain int
            net_taxable_value="3,234.56",     # comma only
            deduction_amount="",              # empty → None
            sale_price="0",                   # zero → None (Bloustein convention)
        ),
    ]
    csv = _write_csv(tmp_path / "mod_iv_2020.csv", rows)
    df = parse_bloustein_year(csv, 2020)
    assert len(df) == 1
    assert df["land_value"].iloc[0] == Decimal("1234.56")
    assert df["improvement_value"].iloc[0] == Decimal("2000")
    assert df["net_value"].iloc[0] == Decimal("3234.56")
    assert df["deductions"].iloc[0] is None
    assert df["sale_price"].iloc[0] is None  # zero treated as missing


def test_parse_bloustein_year_sale_assessment_null_when_no_sale(tmp_path):
    csv = _write_csv(tmp_path / "mod_iv_2020.csv", _five_typical_rows())
    df = parse_bloustein_year(csv, 2020)
    # Row 2 had no sale (filtered to a unique row by prop_loc)
    no_sale = df[df["prop_loc"] == "102 RIVER RD"]
    assert len(no_sale) == 1
    assert no_sale["sale_price"].iloc[0] is None
    assert no_sale["sale_assessment"].iloc[0] is None


def test_parse_bloustein_year_owner_mailing_address_combined(tmp_path):
    csv = _write_csv(tmp_path / "mod_iv_2020.csv", _five_typical_rows())
    df = parse_bloustein_year(csv, 2020)
    # Row 4: out-of-town owner — Rumson mailing address
    rumson = df[df["prop_loc"] == "324 HARDING ROAD"]
    assert len(rumson) == 1
    addr = rumson["owner_mailing_address"].iloc[0]
    assert addr == "29 CIRCLE DRIVE, RUMSON, NJ", f"got {addr!r}"


def test_parse_bloustein_year_year_column_set(tmp_path):
    csv = _write_csv(tmp_path / "mod_iv_2020.csv", _five_typical_rows())
    df = parse_bloustein_year(csv, 2020)
    assert (df["year"] == 2020).all()


def test_parse_bloustein_year_deed_date_iso_parsed(tmp_path):
    csv = _write_csv(tmp_path / "mod_iv_2020.csv", _five_typical_rows())
    df = parse_bloustein_year(csv, 2020)
    sale_row = df[df["prop_loc"] == "100 RIVER RD"]
    assert len(sale_row) == 1
    dd = sale_row["deed_date"].iloc[0]
    assert dd is not None
    assert dd.year == 2020 and dd.month == 6 and dd.day == 15


def test_parse_bloustein_all_concats_multiple_years(tmp_path):
    _write_csv(tmp_path / "mod_iv_2020.csv", _five_typical_rows())
    _write_csv(tmp_path / "mod_iv_2021.csv", _five_typical_rows())
    df = parse_bloustein_all(tmp_path)
    years = sorted(df["year"].unique())
    assert years == [2020, 2021]
    # 4 valid rows × 2 years = 8
    assert len(df) == 8


def test_parse_bloustein_all_empty_dir_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_bloustein_all(tmp_path)


def test_parse_bloustein_year_missing_csv_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_bloustein_year(tmp_path / "does_not_exist.csv", 2020)


def test_canonical_cols_has_18_fields():
    assert len(CANONICAL_HISTORY_COLS) == 18


def test_bloustein_to_canonical_includes_required_sources():
    """Required source columns from D-34 must all be in the rename map."""
    required = {
        "property_id_blk", "property_id_lot", "property_id_qualifier",
        "property_location", "building_description", "calculated_acreage",
        "land_value", "improvement_value", "net_taxable_value",
        "deduction_amount", "deed_book", "deed_page", "deed_date_MMDDYY",
        "sale_price", "sale_assessment", "sale_sr1a_non_usable_code",
        "year_constructed", "number_of_dwellings",
        "street_address", "city_state",
    }
    missing = required - set(BLOUSTEIN_TO_CANONICAL.keys())
    assert not missing, f"missing rename entries: {missing}"
