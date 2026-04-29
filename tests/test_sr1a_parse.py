"""SR1A parser tests using synthetic fixed-width record fixtures.

SR1A is fixed-width 663-byte records. These tests build records by
field-position so they exercise the actual parser path used in production.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

from fairhaven_tax.ingest.pams_pin import build_pams_pin
from fairhaven_tax.ingest.sr1a import FIELDS, RECORD_LENGTH
from fairhaven_tax.ingest.sr1a.parse import parse_sr1a_year


def _build_record(**fields) -> str:
    """Construct a 663-byte SR1A record. Unspecified fields are zero-filled."""
    record = list(" " * RECORD_LENGTH)
    for name, value in fields.items():
        start, length = FIELDS[name]
        s = str(value)
        # Layout convention: numeric fields are zero-padded right; suffixes are
        # right-justified in their width; text fields are left-justified.
        # Use right-justification for numeric-looking values to match real format.
        if name in ("nu_code", "block_suffix", "lot_suffix", "qualification_codes",
                    "property_class", "un_type"):
            # Left-justified text fields
            s = s.ljust(length)[:length]
        else:
            # Right-justified, zero-padded for numeric content
            if s.replace("-", "").isdigit():
                s = s.zfill(length)[:length]
            else:
                s = s.ljust(length)[:length]
        for i, c in enumerate(s):
            record[start - 1 + i] = c
    return "".join(record)


def _fh_record(**overrides) -> str:
    """Build a Fair-Haven valid arms-length record with default values."""
    defaults = dict(
        county_code="13",
        district_code="14",
        nu_code="",            # blank → arms-length
        deed_date="240615",     # YYMMDD = 2024-06-15
        reported_sales_price="000750000",
        verified_sales_price="000750000",
        block="00077",
        lot="00080",
        qualification_codes="",
        property_class="2  ",
        year_built="2010",
        living_space="0002500",
        main_assessed_total="000700000",
        deed_book="9999",
        deed_page="1234",
    )
    defaults.update(overrides)
    return _build_record(**defaults)


def _make_zip(tmp_path: Path, year: int, records: list[str]) -> Path:
    """Pack records into a Sales{YYYY}.zip with inner Sales{YYYY}.txt."""
    txt = "\n".join(records) + "\n"
    archive = tmp_path / f"Sales{year}.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(f"Sales{year}.txt", txt)
    return archive


def test_arms_length_filter(tmp_path):
    """Blank NU = arms-length; codes 01-33 are non-usable."""
    records = [
        _fh_record(nu_code=""),     # accept
        _fh_record(nu_code="0  "),  # accept
        _fh_record(nu_code="00 "),  # accept
        _fh_record(nu_code="07 "),  # reject (related parties)
        _fh_record(nu_code="27 "),  # reject (physical change)
        _fh_record(nu_code="33 "),  # reject (utility transfer)
    ]
    archive = _make_zip(tmp_path, 2025, records)
    sales, rej = parse_sr1a_year(archive, 2025)
    assert len(sales) == 3
    assert len(rej) == 3
    for reason in rej["rejection_reason"]:
        assert reason.startswith("nu_code_not_arms_length:")


def test_district_filter(tmp_path):
    """Only county=13 + district=14 records survive."""
    records = [
        _fh_record(county_code="13", district_code="14"),  # accept (FH)
        _fh_record(county_code="13", district_code="13"),  # silently dropped (not FH)
        _fh_record(county_code="01", district_code="14"),  # silently dropped
    ]
    archive = _make_zip(tmp_path, 2025, records)
    sales, rej = parse_sr1a_year(archive, 2025)
    assert len(sales) == 1
    # Non-FH records are filtered before any rejection bookkeeping
    assert len(rej) == 0


def test_unparseable_date_routes_to_rejection(tmp_path):
    """Date '000000' (placeholder) falls back to date_recorded; both blank → rejection."""
    records = [_fh_record(deed_date="000000", date_recorded="000000")]
    archive = _make_zip(tmp_path, 2025, records)
    sales, rej = parse_sr1a_year(archive, 2025)
    assert len(sales) == 0
    assert len(rej) == 1
    assert rej["rejection_reason"].iloc[0] == "unparseable_date"


def test_pams_pin_construction_with_suffixes(tmp_path):
    """SR1A LOT=00080, LOT_SUFFIX=02 → '1314_77_80.02'."""
    records = [_fh_record(block="00077", lot="00080", lot_suffix="02 ")]
    archive = _make_zip(tmp_path, 2025, records)
    sales, _ = parse_sr1a_year(archive, 2025)
    assert len(sales) == 1
    expected = build_pams_pin("1314", "00077", "00080", lot_suffix="02")
    assert sales["parcel_pin"].iloc[0] == expected
    assert sales["parcel_pin"].iloc[0] == "1314_77_80.02"


def test_pams_pin_no_suffix(tmp_path):
    """Block/lot with empty suffix → 3-part PIN."""
    records = [_fh_record(block="00077", lot="00080")]
    archive = _make_zip(tmp_path, 2025, records)
    sales, _ = parse_sr1a_year(archive, 2025)
    assert sales["parcel_pin"].iloc[0] == "1314_77_80"


def test_missing_block_or_lot_routes_to_rejection(tmp_path):
    records = [_fh_record(block="00000", lot="00080")]
    archive = _make_zip(tmp_path, 2025, records)
    sales, rej = parse_sr1a_year(archive, 2025)
    assert len(sales) == 0
    assert rej["rejection_reason"].iloc[0] == "missing_block_or_lot"


def test_living_space_captured(tmp_path):
    """Living space (sqft proxy from SR1A field) is preserved on accepted rows."""
    records = [_fh_record(living_space="0003200")]
    archive = _make_zip(tmp_path, 2025, records)
    sales, _ = parse_sr1a_year(archive, 2025)
    assert sales["living_space"].iloc[0] == 3200
