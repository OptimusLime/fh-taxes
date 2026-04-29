"""SR1A parser tests using synthetic CSV-in-zip fixtures."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from fairhaven_tax.ingest.pams_pin import build_pams_pin
from fairhaven_tax.ingest.sr1a.parse import parse_sr1a_year


SR1A_HEADERS = [
    "DISTRICT", "BLOCK", "LOT", "QUALIFIER", "PROPERTY_CLASS",
    "SALE_DATE", "SALE_PRICE", "NU_CODE", "DEED_BOOK", "DEED_PAGE",
    "GRANTOR_REDACTED",
]


def _make_zip(tmp_path: Path, year: int, rows: list[dict]) -> Path:
    df = pd.DataFrame(rows, columns=SR1A_HEADERS)
    csv_text = df.to_csv(index=False)
    archive = tmp_path / f"sr1a-{year}.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(f"sr1a-{year}.csv", csv_text)
    return archive


def _row(district="14", block="101", lot="5", qualifier="", pc="2",
         sale_date="01/15/2025", sale_price="500000", nu_code="0",
         deed_book="DB1", deed_page="100", grantor_redacted="true") -> dict:
    return {
        "DISTRICT": district, "BLOCK": block, "LOT": lot, "QUALIFIER": qualifier,
        "PROPERTY_CLASS": pc, "SALE_DATE": sale_date, "SALE_PRICE": sale_price,
        "NU_CODE": nu_code, "DEED_BOOK": deed_book, "DEED_PAGE": deed_page,
        "GRANTOR_REDACTED": grantor_redacted,
    }


def test_arms_length_filter(tmp_path):
    rows = [
        _row(nu_code="0"),    # accept
        _row(nu_code="07"),   # accept
        _row(nu_code="26"),   # accept
        _row(nu_code="99"),   # reject
        _row(nu_code="8"),    # reject (becomes "08", not in set)
    ]
    archive = _make_zip(tmp_path, 2025, rows)
    sales, rej = parse_sr1a_year(archive, 2025)
    assert len(sales) == 3
    assert len(rej) == 2
    assert set(rej["rejection_reason"]) == {"nu_code_not_arms_length"}


def test_district_filter(tmp_path):
    rows = [
        _row(district="14", nu_code="0"),
        _row(district="13", nu_code="0"),
        _row(district="15", nu_code="0"),
    ]
    archive = _make_zip(tmp_path, 2025, rows)
    sales, rej = parse_sr1a_year(archive, 2025)
    assert len(sales) == 1
    assert len(rej) == 2
    assert set(rej["rejection_reason"]) == {"district_not_fair_haven"}


def test_unparseable_date_routes_to_rejection(tmp_path):
    rows = [_row(sale_date="INVALID", nu_code="0")]
    archive = _make_zip(tmp_path, 2025, rows)
    sales, rej = parse_sr1a_year(archive, 2025)
    assert len(sales) == 0
    assert len(rej) == 1
    assert rej["rejection_reason"].iloc[0] == "unparseable_date"


def test_zfill_district(tmp_path):
    # District "4" zfills to "04", which != "14"; should be rejected as not-FH.
    rows = [_row(district="4", nu_code="0")]
    archive = _make_zip(tmp_path, 2025, rows)
    sales, rej = parse_sr1a_year(archive, 2025)
    assert len(sales) == 0
    assert len(rej) == 1
    assert rej["rejection_reason"].iloc[0] == "district_not_fair_haven"


def test_pams_pin_constructed(tmp_path):
    rows = [_row(district="14", block="101", lot="5.01", qualifier="Q1", nu_code="0")]
    archive = _make_zip(tmp_path, 2025, rows)
    sales, _ = parse_sr1a_year(archive, 2025)
    assert len(sales) == 1
    expected = build_pams_pin("14", "101", "5.01", "Q1")
    assert sales["parcel_pin"].iloc[0] == expected


def test_nu_code_zero_normalization(tmp_path):
    # Both "0" and "00" must classify as arms-length (D-12 special case).
    rows = [
        _row(nu_code="0"),
        _row(nu_code="00"),
    ]
    archive = _make_zip(tmp_path, 2025, rows)
    sales, rej = parse_sr1a_year(archive, 2025)
    assert len(sales) == 2
    assert len(rej) == 0
    assert set(sales["nu_code"]) == {"0"}
