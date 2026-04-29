"""Validation gate tests (D-11 thresholds)."""
from __future__ import annotations

from decimal import Decimal

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from fairhaven_tax import constants
from fairhaven_tax.validate.gates import (
    run_all_gates,
    validate_aggregate_assessed,
    validate_parcel_count,
    validate_sales_floor,
)


def _parcels(n: int, value_each: Decimal | None = None) -> gpd.GeoDataFrame:
    if value_each is None:
        # Default: hits the expected aggregate (2.77B / 2200 each)
        value_each = constants.EXPECTED_AGGREGATE_ASSESSED / Decimal(constants.EXPECTED_PARCEL_COUNT)
    df = pd.DataFrame({
        "pams_pin": [f"14_{i}_1_" for i in range(n)],
        "assessed_value": [value_each] * n,
    })
    return gpd.GeoDataFrame(df, geometry=[Point(0, 0)] * n, crs="EPSG:3424")


def test_parcel_count_passes_at_2200():
    g = _parcels(2200)
    r = validate_parcel_count(g)
    assert r.passed is True


def test_parcel_count_fails_at_3000():
    g = _parcels(3000)
    r = validate_parcel_count(g)
    assert r.passed is False
    assert "pct_diff" in r.message


def test_parcel_count_passes_at_5pct_boundary():
    # -5% boundary: 2090
    r1 = validate_parcel_count(_parcels(2090))
    assert r1.passed is True
    # +5% boundary: 2310
    r2 = validate_parcel_count(_parcels(2310))
    assert r2.passed is True


def test_aggregate_assessed_within_5pct():
    # 2.7B → ~2.5% under, should pass
    n = constants.EXPECTED_PARCEL_COUNT
    each_pass = Decimal("2_700_000_000") / Decimal(n)
    r_pass = validate_aggregate_assessed(_parcels(n, each_pass))
    assert r_pass.passed is True
    # 2.5B → ~9.7% under, should fail
    each_fail = Decimal("2_500_000_000") / Decimal(n)
    r_fail = validate_aggregate_assessed(_parcels(n, each_fail))
    assert r_fail.passed is False


def test_sales_floor_at_threshold():
    df200 = pd.DataFrame({"parcel_pin": [f"p{i}" for i in range(200)]})
    df199 = pd.DataFrame({"parcel_pin": [f"p{i}" for i in range(199)]})
    assert validate_sales_floor(df200).passed is True
    assert validate_sales_floor(df199).passed is False


def test_run_all_gates_writes_report(tmp_path):
    g = _parcels(2200)
    sales = pd.DataFrame({"parcel_pin": [f"p{i}" for i in range(250)]})
    ok, results = run_all_gates(g, sales, processed_dir=tmp_path)
    assert ok is True
    assert (tmp_path / "validation_report.parquet").exists()
    import pyarrow.parquet as pq
    table = pq.read_table(tmp_path / "validation_report.parquet")
    assert table.num_rows == 3


def test_validate_phase1_hard_fails_writes_artifact(tmp_path, monkeypatch):
    """D-09 hard-fail: synthetic out-of-tolerance fixture → exit non-zero +
    _VALIDATION-FAILED.md written. This test exercises the CLI driver."""
    import sys
    from pathlib import Path
    import geopandas as gpd
    from shapely.geometry import Point

    # Build a fixture with WAY-too-many parcels (hard-fail parcel_count gate)
    n = 5000
    each = constants.EXPECTED_AGGREGATE_ASSESSED / Decimal(n)
    df = pd.DataFrame({
        "pams_pin": [f"14_{i}_1_" for i in range(n)],
        "assessed_value": [each] * n,
    })
    parcels = gpd.GeoDataFrame(df, geometry=[Point(0, 0)] * n, crs="EPSG:3424")
    sales = pd.DataFrame({"parcel_pin": [f"p{i}" for i in range(250)]})

    # Stage parquet inputs in tmp_path/data/processed/
    proc_dir = tmp_path / "data" / "processed"
    proc_dir.mkdir(parents=True)
    parcels.to_parquet(proc_dir / "parcels.parquet")
    import pyarrow as pa, pyarrow.parquet as pq
    pq.write_table(pa.Table.from_pandas(sales, preserve_index=False),
                   proc_dir / "sales.parquet")

    # Run the validate driver in a subprocess from tmp_path so that its
    # PROCESSED = Path("data/processed") relative path resolves there.
    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "scripts" / "validate_phase1.py"
    import subprocess
    rc = subprocess.call(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env={
            "PATH": __import__("os").environ.get("PATH", ""),
            "PYTHONPATH": str(repo_root / "src"),
        },
    )
    assert rc != 0, "validate_phase1.py must exit non-zero on out-of-tolerance"
    fail_doc = proc_dir / "_VALIDATION-FAILED.md"
    assert fail_doc.exists(), "_VALIDATION-FAILED.md was not written"
    text = fail_doc.read_text()
    assert "Phase 1 Validation FAILED" in text
    assert "parcel_count" in text
