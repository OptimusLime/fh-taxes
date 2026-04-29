"""Tests for last-sale resolution + MOD-IV/SR1A reconciliation."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from fairhaven_tax.validate.reconcile import (
    reconcile_last_sale,
    resolve_last_arms_length_sale,
)


def _sales(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["parcel_pin", "sale_date", "sale_price", "nu_code"])


def _parcels(rows: list[dict]) -> gpd.GeoDataFrame:
    df = pd.DataFrame(rows)
    return gpd.GeoDataFrame(
        df, geometry=[Point(0, 0)] * len(df), crs="EPSG:3424"
    )


def test_resolve_max_date():
    sales = _sales([
        {"parcel_pin": "14_1_1_", "sale_date": date(2020, 1, 1),
         "sale_price": Decimal("400000"), "nu_code": "0"},
        {"parcel_pin": "14_1_1_", "sale_date": date(2024, 6, 1),
         "sale_price": Decimal("500000"), "nu_code": "0"},
    ])
    out = resolve_last_arms_length_sale(sales)
    assert len(out) == 1
    assert out["last_sale_date"].iloc[0] == date(2024, 6, 1)
    assert out["last_sale_price"].iloc[0] == Decimal("500000")


def test_tie_break_max_price():
    """D-18 explicit: same date → keep MAX(sale_price)."""
    sales = _sales([
        {"parcel_pin": "14_1_1_", "sale_date": date(2024, 6, 1),
         "sale_price": Decimal("400000"), "nu_code": "0"},
        {"parcel_pin": "14_1_1_", "sale_date": date(2024, 6, 1),
         "sale_price": Decimal("600000"), "nu_code": "0"},
    ])
    out = resolve_last_arms_length_sale(sales)
    assert len(out) == 1
    assert out["last_sale_price"].iloc[0] == Decimal("600000")


def test_reconcile_emits_diff_when_dates_differ():
    parcels = _parcels([{
        "pams_pin": "14_1_1_",
        "modiv_last_sale_date": date(2022, 1, 1),
        "modiv_last_sale_price": Decimal("500000"),
        "modiv_last_sale_nu_code": "0",
    }])
    sales = _sales([{
        "parcel_pin": "14_1_1_", "sale_date": date(2024, 1, 1),
        "sale_price": Decimal("500000"), "nu_code": "0",
    }])
    _, diffs = reconcile_last_sale(parcels, sales)
    assert len(diffs) == 1
    assert diffs["date_diff_days"].iloc[0] > 180


def test_reconcile_no_diff_within_tolerance():
    parcels = _parcels([{
        "pams_pin": "14_1_1_",
        "modiv_last_sale_date": date(2024, 1, 1),
        "modiv_last_sale_price": Decimal("500000"),
        "modiv_last_sale_nu_code": "0",
    }])
    sales = _sales([{
        "parcel_pin": "14_1_1_", "sale_date": date(2024, 1, 1),
        "sale_price": Decimal("502000"),  # 0.4% diff
        "nu_code": "0",
    }])
    _, diffs = reconcile_last_sale(parcels, sales)
    assert len(diffs) == 0


def test_reconcile_source_assignment():
    parcels = _parcels([
        # has SR1A → "sr1a"
        {"pams_pin": "14_1_1_", "modiv_last_sale_date": None,
         "modiv_last_sale_price": None, "modiv_last_sale_nu_code": None},
        # only MOD-IV → "modiv"
        {"pams_pin": "14_2_2_",
         "modiv_last_sale_date": date(2020, 1, 1),
         "modiv_last_sale_price": Decimal("400000"),
         "modiv_last_sale_nu_code": "0"},
        # neither → null
        {"pams_pin": "14_3_3_", "modiv_last_sale_date": None,
         "modiv_last_sale_price": None, "modiv_last_sale_nu_code": None},
    ])
    sales = _sales([{
        "parcel_pin": "14_1_1_", "sale_date": date(2024, 1, 1),
        "sale_price": Decimal("500000"), "nu_code": "0",
    }])
    out, _ = reconcile_last_sale(parcels, sales)
    sources = dict(zip(out["pams_pin"], out["last_sale_source"]))
    assert sources["14_1_1_"] == "sr1a"
    assert sources["14_2_2_"] == "modiv"
    # null source — pandas may coerce None to NaN in a string column
    third = sources["14_3_3_"]
    assert third is None or (isinstance(third, float) and pd.isna(third))
