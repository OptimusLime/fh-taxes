"""Validation gate tests, calibrated to real Fair Haven data."""
from __future__ import annotations

from decimal import Decimal

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from fairhaven_tax import constants
from fairhaven_tax.validate.gates import (
    run_all_gates,
    validate_aggregate_assessed,
    validate_parcel_count,
    validate_sales_floor,
)


def _parcels(n: int, value_each: Decimal | None = None) -> gpd.GeoDataFrame:
    """Build n synthetic parcels. Default value yields EXPECTED_AGGREGATE_ASSESSED."""
    if value_each is None:
        value_each = constants.EXPECTED_AGGREGATE_ASSESSED / Decimal(constants.EXPECTED_PARCEL_COUNT)
    df = pd.DataFrame({
        "pams_pin": [f"1314_{i}_1" for i in range(n)],
        "assessed_value": [value_each] * n,
    })
    return gpd.GeoDataFrame(df, geometry=[Point(0, 0)] * n, crs="EPSG:3424")


def test_parcel_count_passes_at_expected():
    """At EXPECTED_PARCEL_COUNT (2064), pct_diff is 0 → passes."""
    g = _parcels(constants.EXPECTED_PARCEL_COUNT)
    assert validate_parcel_count(g).passed is True


def test_parcel_count_fails_outside_tolerance():
    """3000 vs 2064 = 45% drift → hard-fail."""
    r = validate_parcel_count(_parcels(3000))
    assert r.passed is False
    assert "pct_diff" in r.message


def test_parcel_count_passes_at_5pct_boundaries():
    """±5% tolerance on EXPECTED_PARCEL_COUNT=2064 = 1961-2167."""
    expected = constants.EXPECTED_PARCEL_COUNT
    low = int(expected * 0.95)   # 1960 (just outside) – use 1961 for inside
    high = int(expected * 1.05)  # 2167
    assert validate_parcel_count(_parcels(low + 1)).passed is True
    assert validate_parcel_count(_parcels(high)).passed is True


def test_aggregate_assessed_within_5pct():
    n = constants.EXPECTED_PARCEL_COUNT
    # 2.5% under expected — should pass
    each_pass = (constants.EXPECTED_AGGREGATE_ASSESSED * Decimal("0.975")) / Decimal(n)
    assert validate_aggregate_assessed(_parcels(n, each_pass)).passed is True
    # 10% under expected — should fail
    each_fail = (constants.EXPECTED_AGGREGATE_ASSESSED * Decimal("0.90")) / Decimal(n)
    assert validate_aggregate_assessed(_parcels(n, each_fail)).passed is False


def test_sales_floor_at_threshold():
    """Floor is SR1A_MIN_ARMS_LENGTH_SALES = 100. Real data has ~197."""
    floor = constants.SR1A_MIN_ARMS_LENGTH_SALES
    df_at = pd.DataFrame({"parcel_pin": [f"p{i}" for i in range(floor)]})
    df_below = pd.DataFrame({"parcel_pin": [f"p{i}" for i in range(floor - 1)]})
    assert validate_sales_floor(df_at).passed is True
    assert validate_sales_floor(df_below).passed is False


def test_run_all_gates_writes_report(tmp_path):
    g = _parcels(constants.EXPECTED_PARCEL_COUNT)
    sales = pd.DataFrame({"parcel_pin": [f"p{i}" for i in range(150)]})
    ok, results = run_all_gates(g, sales, processed_dir=tmp_path)
    assert ok is True
    assert (tmp_path / "validation_report.parquet").exists()
    import pyarrow.parquet as pq
    table = pq.read_table(tmp_path / "validation_report.parquet")
    assert table.num_rows == 3


def test_validate_phase1_hard_fails_writes_artifact(tmp_path):
    """D-09: out-of-tolerance fixture → exit non-zero + _VALIDATION-FAILED.md."""
    import subprocess
    import sys
    from pathlib import Path

    # 5000 parcels — way over EXPECTED_PARCEL_COUNT, will fail parcel_count gate
    n = 5000
    each = constants.EXPECTED_AGGREGATE_ASSESSED / Decimal(n)
    df = pd.DataFrame({
        "pams_pin": [f"1314_{i}_1" for i in range(n)],
        "assessed_value": [each] * n,
    })
    parcels = gpd.GeoDataFrame(df, geometry=[Point(0, 0)] * n, crs="EPSG:3424")
    sales = pd.DataFrame({"parcel_pin": [f"p{i}" for i in range(150)]})

    proc_dir = tmp_path / "data" / "processed"
    proc_dir.mkdir(parents=True)
    parcels.to_parquet(proc_dir / "parcels.parquet")
    import pyarrow as pa, pyarrow.parquet as pq
    pq.write_table(pa.Table.from_pandas(sales, preserve_index=False),
                   proc_dir / "sales.parquet")

    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "scripts" / "validate_phase1.py"
    import os
    rc = subprocess.call(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env={"PATH": os.environ.get("PATH", ""),
             "PYTHONPATH": str(repo_root / "src")},
    )
    assert rc != 0, "validate_phase1.py must exit non-zero on out-of-tolerance"
    fail_doc = proc_dir / "_VALIDATION-FAILED.md"
    assert fail_doc.exists(), "_VALIDATION-FAILED.md was not written"
    text = fail_doc.read_text()
    assert "FAILED" in text
    assert "parcel_count" in text
