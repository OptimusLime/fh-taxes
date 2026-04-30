"""Phase-2 validation gates (D-58 Plan 1).

Range / null-share / cross-source checks over the canonical processed parquets:
  * data/processed/prc.parquet           (D-32 — 57-column schema)
  * data/processed/sales.parquet         (SR1A arms-length sales)
  * data/processed/modiv_history.parquet (D-34 — Bloustein historical with sale_assessment)

Mirrors the dataclass + GateResult shape from validate/gates.py (Phase 1).
`run_phase2_gates` extends `data/processed/validation_report.parquet` with a
`source` column ('phase1' | 'phase2') so the dashboard can distinguish them.

Each gate is a pure function returning GateResult; aggregation is in
`run_phase2_gates`. The Phase-2 CLI driver is `scripts/run_validation.py`.

Schema notes (real data, verified 2026-04-29):
  * prc.parquet uses `pams_pin`, `current_year_assessment`, `acreage`
    (the plan's draft mentioned `current_assessed_total` / `lot_size_acres`
    which are NOT the actual column names — gates target the real schema).
  * sales.parquet uses `parcel_pin` (not `pams_pin`) and lacks an explicit
    `sale_year` column; we derive it from `sale_date` when missing.
  * modiv_history.parquet uses `parcel_pin` and includes `sale_price` +
    `sale_assessment` as the CDF gap-test data source (D-55).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable

import pandas as pd
import pyarrow.parquet as pq

from fairhaven_tax import constants
from fairhaven_tax.persist.parquet_io import (
    ensure_processed_dir,
    write_parquet,
)
# Re-export Phase-1 dataclass + exception so downstream code may
# `from fairhaven_tax.validate import GateResult, ValidationFailure`.
from fairhaven_tax.validate.gates import GateResult, ValidationFailure  # noqa: F401


# Hedonic features per RESEARCH.md §1.5. Real prc column names used.
_HEDONIC_FEATURE_COLS: tuple[str, ...] = (
    "livable_area",
    "bedrooms",
    "bathrooms",
    "condition",
    "quality_grade",
    "year_built",
    "acreage",
)
_NULL_SHARE_TOLERANCE = Decimal("0.05")  # require ≥95% non-null
_PRC_EXPECTED_ROWS = 2060
_PRC_ROW_TOLERANCE = Decimal("0.05")


def _pct_diff(actual: Decimal, expected: Decimal) -> Decimal:
    if expected == 0:
        return Decimal("0")
    return abs(actual - expected) / expected


# ---------------------------------------------------------------------------
# Individual gates
# ---------------------------------------------------------------------------


def validate_prc_required_features(prc_df: pd.DataFrame) -> GateResult:
    """Each hedonic feature column must be ≥95% non-null (RESEARCH.md §1.5).

    `actual` is the worst-case (min) non-null share across the seven feature
    columns; `expected` is 0.95.
    """
    n = len(prc_df)
    if n == 0:
        return GateResult(
            name="prc_required_features",
            expected=Decimal("0.95"),
            actual=Decimal("0"),
            tolerance=_NULL_SHARE_TOLERANCE,
            passed=False,
            message="prc.parquet has zero rows",
        )

    worst_share = Decimal("1")
    worst_col = None
    missing_cols: list[str] = []
    for col in _HEDONIC_FEATURE_COLS:
        if col not in prc_df.columns:
            missing_cols.append(col)
            worst_share = Decimal("0")
            worst_col = col
            continue
        non_null = int(prc_df[col].notna().sum())
        share = Decimal(non_null) / Decimal(n)
        if share < worst_share:
            worst_share = share
            worst_col = col

    passed = (worst_share >= Decimal("0.95")) and not missing_cols
    if missing_cols:
        msg = f"prc missing required columns: {missing_cols}"
    else:
        msg = (
            f"worst non-null share = {worst_share:.4f} on column "
            f"'{worst_col}' (need ≥0.95 across {len(_HEDONIC_FEATURE_COLS)} hedonic features)"
        )
    return GateResult(
        name="prc_required_features",
        expected=Decimal("0.95"),
        actual=worst_share,
        tolerance=_NULL_SHARE_TOLERANCE,
        passed=passed,
        message=msg,
    )


def validate_prc_row_count(prc_df: pd.DataFrame) -> GateResult:
    """Real prc.parquet has 2,060 rows; allow ±5%."""
    actual = int(len(prc_df))
    expected = _PRC_EXPECTED_ROWS
    pct = _pct_diff(Decimal(actual), Decimal(expected))
    passed = pct <= _PRC_ROW_TOLERANCE
    return GateResult(
        name="prc_row_count",
        expected=expected,
        actual=actual,
        tolerance=_PRC_ROW_TOLERANCE,
        passed=passed,
        message=(
            f"prc rows {actual} vs expected {expected} "
            f"(pct_diff={pct:.4f}, tolerance={_PRC_ROW_TOLERANCE})"
        ),
    )


def validate_sales_row_count(sales_df: pd.DataFrame) -> GateResult:
    """SR1A arms-length sales floor (constants.SR1A_MIN_ARMS_LENGTH_SALES)."""
    actual = int(len(sales_df))
    expected = constants.SR1A_MIN_ARMS_LENGTH_SALES
    passed = actual >= expected
    return GateResult(
        name="sales_row_count",
        expected=expected,
        actual=actual,
        tolerance=None,
        passed=passed,
        message=f"sales rows {actual} (floor={expected})",
    )


def _derive_sale_years(sales_df: pd.DataFrame) -> pd.Series:
    """Use `sale_year` if present; otherwise extract year from `sale_date`."""
    if "sale_year" in sales_df.columns:
        return pd.to_numeric(sales_df["sale_year"], errors="coerce").astype("Int64")
    if "sale_date" in sales_df.columns:
        return pd.to_datetime(sales_df["sale_date"], errors="coerce").dt.year.astype("Int64")
    return pd.Series([pd.NA] * len(sales_df), dtype="Int64")


def validate_sales_year_range(sales_df: pd.DataFrame) -> GateResult:
    """Every derivable sale year ∈ [2020, 2025]."""
    years = _derive_sale_years(sales_df).dropna()
    if len(years) == 0:
        return GateResult(
            name="sales_year_range",
            expected=Decimal("0"),
            actual=Decimal("0"),
            tolerance=None,
            passed=False,
            message="sales: no sale_year or sale_date column populated",
        )
    out_of_range = int(((years < 2020) | (years > 2025)).sum())
    passed = out_of_range == 0
    return GateResult(
        name="sales_year_range",
        expected=0,
        actual=out_of_range,
        tolerance=None,
        passed=passed,
        message=(
            f"sales out of [2020, 2025]: {out_of_range} of {len(years)} "
            f"(min={int(years.min())}, max={int(years.max())})"
        ),
    )


def validate_modiv_history_sale_assessment(modiv_history_df: pd.DataFrame) -> GateResult:
    """Post-ADP (D-55) rows with both sale_price AND sale_assessment.

    The CDF gap test (Plan 7) requires at least
    constants.CDF_TEST_MIN_N (=30) such rows in
    [CDF_TEST_YEAR_MIN, CDF_TEST_YEAR_MAX].
    """
    needed_cols = {"year", "sale_price", "sale_assessment"}
    missing = needed_cols - set(modiv_history_df.columns)
    if missing:
        return GateResult(
            name="modiv_history_sale_assessment",
            expected=constants.CDF_TEST_MIN_N,
            actual=0,
            tolerance=None,
            passed=False,
            message=f"modiv_history missing columns: {sorted(missing)}",
        )
    df = modiv_history_df
    in_window = (
        (df["year"] >= constants.CDF_TEST_YEAR_MIN)
        & (df["year"] <= constants.CDF_TEST_YEAR_MAX)
        & df["sale_price"].notna()
        & df["sale_assessment"].notna()
    )
    actual = int(in_window.sum())
    expected = constants.CDF_TEST_MIN_N
    passed = actual >= expected
    return GateResult(
        name="modiv_history_sale_assessment",
        expected=expected,
        actual=actual,
        tolerance=None,
        passed=passed,
        message=(
            f"modiv_history rows in [{constants.CDF_TEST_YEAR_MIN},"
            f"{constants.CDF_TEST_YEAR_MAX}] with sale_price+sale_assessment: {actual} "
            f"(min for CDF gap test = {expected})"
        ),
    )


def _pin_set(df: pd.DataFrame, *candidates: str) -> set[str]:
    for col in candidates:
        if col in df.columns:
            return set(df[col].dropna().astype(str).tolist())
    return set()


def validate_cross_source_pin_alignment(
    prc_df: pd.DataFrame,
    sales_df: pd.DataFrame,
    modiv_history_df: pd.DataFrame,
) -> GateResult:
    """Every PIN in sales must appear in BOTH prc and modiv_history.

    Pass iff alignment_rate ≥ 0.95.
    """
    sales_pins = _pin_set(sales_df, "parcel_pin", "pams_pin")
    prc_pins = _pin_set(prc_df, "pams_pin", "parcel_pin")
    modiv_pins = _pin_set(modiv_history_df, "parcel_pin", "pams_pin")

    if not sales_pins:
        return GateResult(
            name="cross_source_pin_alignment",
            expected=Decimal("0.95"),
            actual=Decimal("0"),
            tolerance=None,
            passed=False,
            message="sales has no PIN column or is empty",
        )

    aligned = sales_pins & prc_pins & modiv_pins
    rate = Decimal(len(aligned)) / Decimal(len(sales_pins))
    passed = rate >= Decimal("0.95")
    return GateResult(
        name="cross_source_pin_alignment",
        expected=Decimal("0.95"),
        actual=rate,
        tolerance=None,
        passed=passed,
        message=(
            f"sales PIN alignment rate = {rate:.4f} "
            f"({len(aligned)}/{len(sales_pins)} present in both prc and modiv_history)"
        ),
    )


def validate_no_negative_assessments(prc_df: pd.DataFrame) -> GateResult:
    """`current_year_assessment` must have zero negative values (D-32 schema)."""
    col = "current_year_assessment"
    if col not in prc_df.columns:
        # Plan-stated alt name; defensive fallback.
        col = "current_assessed_total" if "current_assessed_total" in prc_df.columns else col
    if col not in prc_df.columns:
        return GateResult(
            name="no_negative_assessments",
            expected=0,
            actual=0,
            tolerance=None,
            passed=False,
            message=f"prc missing assessment column ({col})",
        )

    series = pd.to_numeric(prc_df[col], errors="coerce")
    negatives = int((series < 0).sum())
    passed = negatives == 0
    return GateResult(
        name="no_negative_assessments",
        expected=0,
        actual=negatives,
        tolerance=None,
        passed=passed,
        message=f"negative assessments in '{col}': {negatives}",
    )


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------


def _result_row(r: GateResult, source: str) -> dict:
    return {
        "gate_name": r.name,
        "expected": str(r.expected),
        "actual": str(r.actual),
        "tolerance": str(r.tolerance) if r.tolerance is not None else None,
        "passed": bool(r.passed),
        "message": r.message,
        "source": source,
    }


def _read_existing_report(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        return pq.read_table(path).to_pandas()
    except Exception:
        return None


def run_phase2_gates(
    prc_df: pd.DataFrame,
    sales_df: pd.DataFrame,
    modiv_history_df: pd.DataFrame,
    processed_dir: Path | None = None,
) -> tuple[bool, list[GateResult]]:
    """Run all Phase-2 gates, extend validation_report.parquet, return (ok, results).

    If a Phase-1 report already exists at processed_dir/validation_report.parquet,
    its rows are tagged source='phase1' and the new Phase-2 rows are appended
    with source='phase2'. The combined report replaces the file in one
    atomic-ish write (write_parquet is the single canonical path; pyarrow
    overwrites in-place).
    """
    results: list[GateResult] = [
        validate_prc_required_features(prc_df),
        validate_prc_row_count(prc_df),
        validate_sales_row_count(sales_df),
        validate_sales_year_range(sales_df),
        validate_modiv_history_sale_assessment(modiv_history_df),
        validate_cross_source_pin_alignment(prc_df, sales_df, modiv_history_df),
        validate_no_negative_assessments(prc_df),
    ]

    proc = ensure_processed_dir(processed_dir)
    report_path = proc / "validation_report.parquet"

    existing = _read_existing_report(report_path)
    rows: list[dict] = []
    if existing is not None and len(existing) > 0:
        # Tag pre-existing rows. If they already carry a `source` column,
        # respect it; otherwise mark them 'phase1'.
        if "source" not in existing.columns:
            existing = existing.assign(source="phase1")
        else:
            existing["source"] = existing["source"].fillna("phase1")
        rows.extend(existing.to_dict(orient="records"))

    rows.extend(_result_row(r, "phase2") for r in results)
    df = pd.DataFrame(rows)
    write_parquet(df, report_path)

    all_passed = all(r.passed for r in results)
    return all_passed, results


__all__ = [
    "GateResult",
    "ValidationFailure",
    "validate_prc_required_features",
    "validate_prc_row_count",
    "validate_sales_row_count",
    "validate_sales_year_range",
    "validate_modiv_history_sale_assessment",
    "validate_cross_source_pin_alignment",
    "validate_no_negative_assessments",
    "run_phase2_gates",
]
