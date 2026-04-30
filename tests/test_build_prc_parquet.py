"""Tests for scripts/build_prc_parquet.py — aggregator helpers.

Covers:
  - _aggregate_parcel happy path (m4 + sr + prc.pdf + ch75.pdf + taxlist.pdf
    fixtures all present → row dict has all expected keys + sale_rows non-empty).
  - _aggregate_parcel skip path (no m4.html → returns (None, [])).
  - _cross_validate_sqft flags >10% mismatch and ignores ≤10%.

Fixtures from tests/fixtures/oprs/ are already sanitized real OPRS responses
for parcel 1314_30_1. We assemble them into a parcel directory under
tmp_path so the script's filename conventions are honored:
    {pin}/m4.html, sr_*.html, prc.pdf, ch75.pdf, taxlist_2026.pdf.
"""
from __future__ import annotations

import shutil
import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

# Make scripts/ importable so we can import build_prc_parquet helpers.
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import build_prc_parquet  # noqa: E402

FIXT = Path(__file__).resolve().parent / "fixtures" / "oprs"


def _make_parcel_dir(tmp_path: Path, pin: str, *, with_m4=True,
                     with_sr=True, with_prc=True, with_ch75=True,
                     with_taxlist=True) -> Path:
    """Assemble a parcel directory mirroring data/raw/oprs_prc/<pin>/ layout."""
    p = tmp_path / pin
    p.mkdir(parents=True, exist_ok=True)
    if with_m4:
        shutil.copy(FIXT / "m4_sample.html", p / "m4.html")
    if with_sr:
        shutil.copy(FIXT / "sr_sample.html", p / "sr_401.html")
    if with_prc:
        shutil.copy(FIXT / "prc_sample.pdf", p / "prc.pdf")
    if with_ch75:
        shutil.copy(FIXT / "ch75_sample.pdf", p / "ch75.pdf")
    if with_taxlist:
        shutil.copy(FIXT / "taxlist_sample.pdf", p / "taxlist_2026.pdf")
    return p


def test_aggregate_parcel_happy_path(tmp_path):
    """All five components present → row dict carries every canonical field."""
    parcel = _make_parcel_dir(tmp_path, "1314_30_1")
    row, sale_rows = build_prc_parquet._aggregate_parcel(parcel)

    assert row is not None
    # pams_pin is the directory name (canonical key).
    assert row["pams_pin"] == "1314_30_1"
    # M4-derived fields.
    assert row["block"] == "30"
    assert row["lot"] == "1"
    assert row["square_ft"] == 1763
    # PRC-PDF-derived (non-None on real fixture).
    assert row.get("livable_area") is not None
    assert row.get("bedrooms") is not None
    assert row.get("bathrooms") is not None
    assert row.get("condition") is not None
    # ch75-derived.
    assert row.get("current_year_assessment") is not None
    assert row.get("prior_year_assessment") is not None
    # taxlist-derived (parcel 30/1 is in the fixture page).
    assert row.get("actual_tax_paid_total") is not None
    assert row.get("tax_1h_paid") is not None
    # SR sale rows captured (1 fixture sr file).
    assert len(sale_rows) == 1
    assert sale_rows[0]["parcel_pin"] == "1314_30_1"


def test_aggregate_parcel_missing_m4_returns_none(tmp_path):
    """Parcel dir without m4.html → (None, []) so script can log + skip."""
    parcel = _make_parcel_dir(tmp_path, "1314_30_1", with_m4=False)
    row, sale_rows = build_prc_parquet._aggregate_parcel(parcel)
    assert row is None
    assert sale_rows == []


def test_aggregate_parcel_missing_pdfs_still_returns_row(tmp_path):
    """Parcel with m4 but no PDFs → row carries M4 fields + None for PDF fields."""
    parcel = _make_parcel_dir(tmp_path, "1314_30_1",
                              with_prc=False, with_ch75=False, with_taxlist=False)
    row, sale_rows = build_prc_parquet._aggregate_parcel(parcel)
    assert row is not None
    assert row["pams_pin"] == "1314_30_1"
    assert row["block"] == "30"
    # PDF-derived fields exist as keys but are None.
    from fairhaven_tax.ingest.oprs.parse_prc_pdf import PRC_PDF_FIELDS
    from fairhaven_tax.ingest.oprs.parse_ch75_pdf import CH75_FIELDS
    from fairhaven_tax.ingest.oprs.parse_taxlist_pdf import TAXLIST_FIELDS
    for k in PRC_PDF_FIELDS:
        assert k in row, f"missing PRC field: {k}"
        assert row[k] is None or row[k] == [] or row[k] == 0, k
    for k in CH75_FIELDS:
        assert k in row, f"missing CH75 field: {k}"
    for k in TAXLIST_FIELDS:
        assert k in row, f"missing TAXLIST field: {k}"


def test_cross_validate_sqft_flags_10pct_mismatch():
    """Parcels diverging >10% between m4.square_ft and prc livable_area are flagged."""
    df = pd.DataFrame([
        # Match within tolerance (5% diff): 1000 vs 1050 → ignored.
        {"pams_pin": "1314_1_1", "square_ft": 1000, "livable_area": Decimal("1050")},
        # Big gap (50% diff): 2000 vs 1000 → flagged.
        {"pams_pin": "1314_1_2", "square_ft": 2000, "livable_area": Decimal("1000")},
        # One side missing → ignored (cannot compare).
        {"pams_pin": "1314_1_3", "square_ft": None, "livable_area": Decimal("900")},
        {"pams_pin": "1314_1_4", "square_ft": 1500, "livable_area": None},
    ])
    diffs = build_prc_parquet._cross_validate_sqft(df)
    assert len(diffs) == 1
    assert diffs.iloc[0]["pams_pin"] == "1314_1_2"
    assert diffs.iloc[0]["abs_diff_pct"] > 10
