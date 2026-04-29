"""SR1A fixed-width parser.

Reads NJ DOT SR1A annual `Sales{YYYY}.zip` archives, slices fields per the
documented 663-byte record layout (see `fairhaven_tax.ingest.sr1a.FIELDS`),
filters to Fair Haven (county=13, district=14), and routes non-arms-length
or unparseable rows to a rejections frame with controlled-vocabulary reasons.

Arms-length per NJ DOT convention: NU code field is BLANK (or "0"/"00").
Codes 01-33 are the various Non-Usable categories.
"""
from __future__ import annotations

import zipfile
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from fairhaven_tax import constants
from fairhaven_tax.ingest.pams_pin import build_pams_pin
from fairhaven_tax.ingest.sr1a import (
    RECORD_LENGTH,
    archive_for_year,
    inner_filename_for_year,
    slice_field,
)


CANONICAL_SALES_COLS = [
    "parcel_pin",
    "sale_date",
    "sale_price",
    "nu_code",
    "deed_book",
    "deed_page",
    "property_location",
    "property_class",
    "year_built",
    "living_space",
    "main_assessed_total",
    "source_file",
    "source_year",
]

CANONICAL_REJECT_COLS = [
    "parcel_pin",
    "sale_date_raw",
    "sale_price_raw",
    "nu_code",
    "deed_book",
    "deed_page",
    "rejection_reason",
    "source_file",
    "source_year",
]


def _parse_yymmdd(s: str) -> date | None:
    """SR1A dates are YYMMDD. Year < 50 → 20xx; >=50 → 19xx (NJ convention)."""
    s = s.strip()
    if not s or s == "000000" or len(s) != 6 or not s.isdigit():
        return None
    yy = int(s[0:2])
    mm = int(s[2:4])
    dd = int(s[4:6])
    yyyy = 2000 + yy if yy < 50 else 1900 + yy
    try:
        return date(yyyy, mm, dd)
    except ValueError:
        return None


def _parse_int_money(s: str) -> Decimal | None:
    """SR1A money fields are zero-padded integers (cents-or-dollars per field)."""
    s = s.strip()
    if not s or set(s) == {"0"}:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _parse_int(s: str) -> int | None:
    s = s.strip()
    if not s or not s.isdigit():
        return None
    n = int(s)
    return n if n > 0 else None


def _read_records(archive_path: Path, year: int) -> list[str]:
    """Return all 663-byte records as strings (latin-1 decoded, line-terminator stripped)."""
    inner = inner_filename_for_year(year)
    with zipfile.ZipFile(archive_path) as zf:
        members = zf.namelist()
        if inner not in members:
            # Fall back to the first .txt member
            txt_members = [m for m in members if m.lower().endswith(".txt")]
            if not txt_members:
                raise ValueError(f"no .txt member in {archive_path}")
            inner = txt_members[0]
        with zf.open(inner) as f:
            data = f.read().decode("latin-1", errors="replace")
    # Records are line-terminated. Some files use \r\n, some \n. Strip both.
    records: list[str] = []
    for line in data.splitlines():
        if not line:
            continue
        # Pad/truncate to RECORD_LENGTH so slice_field never IndexErrors
        if len(line) < RECORD_LENGTH:
            line = line.ljust(RECORD_LENGTH)
        records.append(line)
    return records


def parse_sr1a_year(archive_path: Path, year: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse one SR1A year archive → (sales_df, rejections_df).

    Filters to Fair Haven (county=13, district=14) at the line level.
    Arms-length filter applied AFTER Fair Haven filter so we count the
    full Fair Haven distribution while only the arms-length subset
    flows to the sales frame.
    """
    archive_path = Path(archive_path)
    records = _read_records(archive_path, year)

    fh_county = constants.SR1A_COUNTY_MONMOUTH
    fh_district = constants.SR1A_DISTRICT_FAIR_HAVEN
    arms_length = constants.ARMS_LENGTH_NU_CODES

    sales_rows: list[dict] = []
    reject_rows: list[dict] = []

    for record in records:
        if len(record) < RECORD_LENGTH:
            continue
        if slice_field(record, "county_code") != fh_county:
            continue
        if slice_field(record, "district_code") != fh_district:
            continue

        # Both filters passed — this is a Fair Haven record.
        nu_raw = slice_field(record, "nu_code")
        block = slice_field(record, "block")
        block_suffix = slice_field(record, "block_suffix")
        lot = slice_field(record, "lot")
        lot_suffix = slice_field(record, "lot_suffix")
        qualifier = slice_field(record, "qualification_codes")
        deed_book = slice_field(record, "deed_book")
        deed_page = slice_field(record, "deed_page")
        deed_date_raw = slice_field(record, "deed_date")
        date_recorded_raw = slice_field(record, "date_recorded")
        reported_price_raw = slice_field(record, "reported_sales_price")
        verified_price_raw = slice_field(record, "verified_sales_price")

        # Build parcel_pin
        if not block.lstrip("0") or not lot.lstrip("0"):
            reject_rows.append({
                "parcel_pin": None,
                "sale_date_raw": deed_date_raw,
                "sale_price_raw": reported_price_raw,
                "nu_code": nu_raw,
                "deed_book": deed_book,
                "deed_page": deed_page,
                "rejection_reason": "missing_block_or_lot",
                "source_file": archive_path.name,
                "source_year": year,
            })
            continue

        parcel_pin = build_pams_pin(
            constants.MUN_CODE_FAIR_HAVEN, block, lot, qualifier,
            block_suffix=block_suffix, lot_suffix=lot_suffix,
        )

        # Date — prefer DEED_DATE, fall back to DATE-RECORDED
        sale_date = _parse_yymmdd(deed_date_raw) or _parse_yymmdd(date_recorded_raw)
        if sale_date is None:
            reject_rows.append({
                "parcel_pin": parcel_pin,
                "sale_date_raw": deed_date_raw,
                "sale_price_raw": reported_price_raw,
                "nu_code": nu_raw,
                "deed_book": deed_book,
                "deed_page": deed_page,
                "rejection_reason": "unparseable_date",
                "source_file": archive_path.name,
                "source_year": year,
            })
            continue

        # Price — prefer VERIFIED, fall back to REPORTED
        sale_price = _parse_int_money(verified_price_raw) or _parse_int_money(reported_price_raw)
        if sale_price is None:
            reject_rows.append({
                "parcel_pin": parcel_pin,
                "sale_date_raw": deed_date_raw,
                "sale_price_raw": reported_price_raw,
                "nu_code": nu_raw,
                "deed_book": deed_book,
                "deed_page": deed_page,
                "rejection_reason": "missing_price",
                "source_file": archive_path.name,
                "source_year": year,
            })
            continue

        # Arms-length filter — blank NU is the canonical arms-length signal
        if nu_raw not in arms_length:
            reject_rows.append({
                "parcel_pin": parcel_pin,
                "sale_date_raw": deed_date_raw,
                "sale_price_raw": reported_price_raw,
                "nu_code": nu_raw,
                "deed_book": deed_book,
                "deed_page": deed_page,
                "rejection_reason": f"nu_code_not_arms_length:{nu_raw or 'BLANK_FAILED'}",
                "source_file": archive_path.name,
                "source_year": year,
            })
            continue

        # Accepted — emit canonical sales row
        sales_rows.append({
            "parcel_pin": parcel_pin,
            "sale_date": sale_date,
            "sale_price": sale_price,
            "nu_code": nu_raw,  # always blank/0/00 for accepted rows; preserved for audit
            "deed_book": deed_book or None,
            "deed_page": deed_page or None,
            "property_location": slice_field(record, "property_location") or None,
            "property_class": slice_field(record, "property_class") or None,
            "year_built": _parse_int(slice_field(record, "year_built")),
            "living_space": _parse_int(slice_field(record, "living_space")),
            "main_assessed_total": _parse_int_money(slice_field(record, "main_assessed_total")),
            "source_file": archive_path.name,
            "source_year": year,
        })

    sales_df = (
        pd.DataFrame(sales_rows, columns=CANONICAL_SALES_COLS)
        if sales_rows else pd.DataFrame(columns=CANONICAL_SALES_COLS)
    )
    rej_df = (
        pd.DataFrame(reject_rows, columns=CANONICAL_REJECT_COLS)
        if reject_rows else pd.DataFrame(columns=CANONICAL_REJECT_COLS)
    )
    return sales_df, rej_df


def parse_sr1a_all(snapshot_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse every Sales{YYYY}.zip in snapshot_dir; concatenate sales + rejections."""
    snapshot_dir = Path(snapshot_dir)
    sales_frames: list[pd.DataFrame] = []
    rej_frames: list[pd.DataFrame] = []
    archives = sorted(snapshot_dir.glob("Sales[0-9][0-9][0-9][0-9].zip"))
    if not archives:
        raise FileNotFoundError(f"no Sales*.zip in {snapshot_dir}")
    for arch in archives:
        # Sales2024.zip → 2024
        try:
            year = int(arch.stem.replace("Sales", ""))
        except ValueError:
            raise ValueError(f"cannot parse year from {arch.name}")
        s, r = parse_sr1a_year(arch, year)
        sales_frames.append(s)
        rej_frames.append(r)

    sales_all = (
        pd.concat(sales_frames, ignore_index=True)
        if sales_frames else pd.DataFrame(columns=CANONICAL_SALES_COLS)
    )
    rej_all = (
        pd.concat(rej_frames, ignore_index=True)
        if rej_frames else pd.DataFrame(columns=CANONICAL_REJECT_COLS)
    )
    return sales_all, rej_all
