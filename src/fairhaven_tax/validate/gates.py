"""Validation gates with hard-fail behavior (D-09 / D-10 / D-11).

Each gate returns a GateResult; run_all_gates aggregates them and writes
data/processed/validation_report.parquet.

The validate_phase1.py driver script writes _VALIDATION-FAILED.md and exits
non-zero when any gate fails. This module raises ValidationFailure on demand.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal
from pathlib import Path

import geopandas as gpd
import pandas as pd

from fairhaven_tax import constants
from fairhaven_tax.persist.parquet_io import write_parquet, ensure_processed_dir


class ValidationFailure(Exception):
    """Raised when one or more validation gates fail."""


@dataclass
class GateResult:
    name: str
    expected: Decimal | int
    actual: Decimal | int
    tolerance: Decimal | None
    passed: bool
    message: str


def _pct_diff(actual: Decimal, expected: Decimal) -> Decimal:
    if expected == 0:
        return Decimal("0")
    return abs(actual - expected) / expected


def validate_parcel_count(parcels_gdf: gpd.GeoDataFrame) -> GateResult:
    """D-11(a): |actual - 2200| / 2200 ≤ 5%."""
    actual = int(len(parcels_gdf))
    expected = constants.EXPECTED_PARCEL_COUNT
    tol = constants.VALIDATION_TOLERANCE
    pct = _pct_diff(Decimal(actual), Decimal(expected))
    passed = pct <= tol
    return GateResult(
        name="parcel_count",
        expected=expected,
        actual=actual,
        tolerance=tol,
        passed=passed,
        message=(
            f"parcel count {actual} vs expected {expected} "
            f"(pct_diff={pct:.4f}, tolerance={tol})"
        ),
    )


def validate_aggregate_assessed(parcels_gdf: gpd.GeoDataFrame) -> GateResult:
    """D-11(b): |Σ assessed - 2.77B| / 2.77B ≤ 5%."""
    total = Decimal("0")
    for v in parcels_gdf["assessed_value"]:
        if v is None:
            continue
        try:
            total += Decimal(str(v))
        except Exception:
            continue
    expected = constants.EXPECTED_AGGREGATE_ASSESSED
    tol = constants.VALIDATION_TOLERANCE
    pct = _pct_diff(total, expected)
    passed = pct <= tol
    return GateResult(
        name="aggregate_assessed",
        expected=expected,
        actual=total,
        tolerance=tol,
        passed=passed,
        message=(
            f"aggregate assessed ${total} vs expected ${expected} "
            f"(pct_diff={pct:.4f}, tolerance={tol})"
        ),
    )


def validate_sales_floor(sales_df: pd.DataFrame) -> GateResult:
    """D-11(c): SR1A 2018-2025 arms-length sales count ≥ 200."""
    actual = int(len(sales_df))
    expected = constants.SR1A_MIN_ARMS_LENGTH_SALES
    passed = actual >= expected
    return GateResult(
        name="sales_floor",
        expected=expected,
        actual=actual,
        tolerance=None,
        passed=passed,
        message=f"arms-length sales 2018-2025: {actual} (floor={expected})",
    )


def run_all_gates(
    parcels_gdf: gpd.GeoDataFrame,
    sales_df: pd.DataFrame,
    processed_dir: Path | None = None,
) -> tuple[bool, list[GateResult]]:
    """Run all gates, write validation_report.parquet, return (all_passed, results)."""
    results = [
        validate_parcel_count(parcels_gdf),
        validate_aggregate_assessed(parcels_gdf),
        validate_sales_floor(sales_df),
    ]
    proc = ensure_processed_dir(processed_dir)
    rows = []
    for r in results:
        rows.append({
            "gate_name": r.name,
            "expected": str(r.expected),
            "actual": str(r.actual),
            "tolerance": str(r.tolerance) if r.tolerance is not None else None,
            "passed": r.passed,
            "message": r.message,
        })
    df = pd.DataFrame(rows)
    write_parquet(df, proc / "validation_report.parquet")
    all_passed = all(r.passed for r in results)
    return all_passed, results
