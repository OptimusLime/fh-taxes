#!/usr/bin/env python
"""Phase 2 Plan 04 — hedonic OLS CLI driver.

Reads `data/processed/{sales,prc,parcels,modiv_history}.parquet`,
fits the hedonic per RESEARCH.md §1.5 (HC3 robust SEs, k-means
neighborhood FE, year FE, Duan's smearing, MODEL-03 calibration),
and writes six artifacts:

  * data/processed/hedonic_fit.parquet         (coefficient table)
  * data/processed/hedonic_predictions.parquet (per-parcel predictions)
  * viz/src/data/overlays/estimated_true_value.json
  * viz/src/data/charts/hedonic_coefficients.vl.json
  * viz/src/data/charts/hedonic_residuals.vl.json
  * viz/src/data/charts/hedonic_choropleth.vl.json

All JSON writes go through `atomic_write_json` (D-63 hot-reload contract).
Parquet writes via `write_parquet` (atomic via pyarrow).

Exit codes (POSIX):
  0 — success (R² ≥ 0.5; warning if < HEDONIC_R2_TARGET=0.7)
  1 — catastrophic R² (< 0.5)
  2 — preflight failure (missing inputs OR Phase-2 validation gates fail)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import geopandas as gpd

from fairhaven_tax import constants
from fairhaven_tax.models.hedonic import (
    choropleth_chart_spec,
    coefficient_chart,
    fit_hedonic,
    residual_chart,
)
from fairhaven_tax.persist.json_io import atomic_write_json
from fairhaven_tax.persist.parquet_io import write_parquet
from fairhaven_tax.validate.checks import run_phase2_gates

PROCESSED = Path("data/processed")
SALES = PROCESSED / "sales.parquet"
PRC = PROCESSED / "prc.parquet"
PARCELS = PROCESSED / "parcels.parquet"
MODIV = PROCESSED / "modiv_history.parquet"

OUT_FIT = PROCESSED / "hedonic_fit.parquet"
OUT_PREDS = PROCESSED / "hedonic_predictions.parquet"

VIZ = Path("viz/src/data")
OUT_OVERLAY = VIZ / "overlays" / "estimated_true_value.json"
OUT_COEF_CHART = VIZ / "charts" / "hedonic_coefficients.vl.json"
OUT_RESID_CHART = VIZ / "charts" / "hedonic_residuals.vl.json"
OUT_CHORO_CHART = VIZ / "charts" / "hedonic_choropleth.vl.json"


def _save_altair_chart_atomically(chart, path: Path) -> None:
    """Render Altair chart to a Vega-Lite spec dict, write atomically.

    Altair's `chart.save(path, format="json")` is non-atomic; we re-emit
    the same dict via `atomic_write_json` to honour D-63.
    """
    atomic_write_json(path, chart.to_dict())


def main() -> int:
    # ---- Preflight: required inputs exist -----------------------------
    missing = [str(p) for p in (SALES, PRC, PARCELS, MODIV) if not p.exists()]
    if missing:
        print(
            f"ERROR: missing inputs {missing}; run Phase 1 + Phase 1.5 first.",
            file=sys.stderr,
        )
        return 2

    # ---- Preflight: Phase-2 validation gates --------------------------
    # Per Plan 02-01 SUMMARY: prc.condition is 84% non-null — a known
    # data-quality finding that Plan 04 explicitly addresses via
    # within-neighborhood median imputation for the universe predict step,
    # and via dropna for the 197-sales training set. So a SOLE failure on
    # prc_required_features (with the worst column being `condition`) is
    # downgraded to a warning here. All other gate failures remain
    # blocking (exit 2). This is the "address condition 84% non-null
    # finding" item from the Plan 02-01 open todos list.
    prc_df = pd.read_parquet(PRC)
    sales_df = pd.read_parquet(SALES)
    modiv_df = pd.read_parquet(MODIV)
    ok, results = run_phase2_gates(prc_df, sales_df, modiv_df)
    if not ok:
        failed = [r for r in results if not r.passed]
        is_only_condition = (
            len(failed) == 1
            and failed[0].name == "prc_required_features"
            and "condition" in failed[0].message
        )
        if is_only_condition:
            print(
                "WARN: gate prc_required_features fails on `condition` "
                f"({failed[0].message}). Hedonic handles this via "
                "within-neighborhood median imputation; continuing.",
                file=sys.stderr,
            )
        else:
            print("ERROR: Phase-2 validation gates failed:", file=sys.stderr)
            for r in failed:
                print(f"  - {r.name}: {r.message}", file=sys.stderr)
            print(
                "Hedonic refuses to fit while gates other than the known "
                "`condition` finding are red. Fix data quality issues "
                "(or revise gate thresholds) and re-run.",
                file=sys.stderr,
            )
            return 2

    # ---- Fit -------------------------------------------------------------
    # k_neighborhood=None → fit_hedonic sweeps {5,6,7,8} and picks max-silhouette
    # (MODEL-01 contract per .planning/phases/02-statistical-pipeline/02-04-PLAN.md
    # important_context: "Default k=6, but try {5,6,7,8} and pick the k with
    # highest mean silhouette score.").
    fit = fit_hedonic(SALES, PRC, PARCELS, k_neighborhood=None)
    if fit.n_obs == 0:
        print(
            "ERROR: zero observations after arms-length + window + "
            "feature-completeness filter — refusing to declare success.",
            file=sys.stderr,
        )
        return 2

    print(
        f"R²={fit.r_squared:.4f}, adj R²={fit.adj_r_squared:.4f}, "
        f"n={fit.n_obs}, params={fit.n_params}, "
        f"obs/param={fit.n_obs/fit.n_params:.2f}, k={fit.k_neighborhood} "
        f"(silhouette={fit.silhouette_score:.3f}), "
        f"calibration={fit.calibration_factor:.4f}, "
        f"smearing={fit.smearing_factor:.4f}"
    )

    # ---- Refuse zero predictions (S2) -----------------------------------
    if len(fit.per_parcel_predictions) == 0:
        print(
            "ERROR: zero per-parcel predictions — refusing to declare success.",
            file=sys.stderr,
        )
        return 2

    # ---- Parquet outputs ------------------------------------------------
    fit_metadata = {
        "n_obs": str(fit.n_obs),
        "n_params": str(fit.n_params),
        "r_squared": f"{fit.r_squared:.6f}",
        "adj_r_squared": f"{fit.adj_r_squared:.6f}",
        "k_neighborhood": str(fit.k_neighborhood),
        "silhouette_score": f"{fit.silhouette_score:.6f}",
        "seed": str(fit.seed),
        "calibration_factor": f"{fit.calibration_factor:.6f}",
        "smearing_factor": f"{fit.smearing_factor:.6f}",
        "feature_summary": json.dumps(fit.feature_summary, default=str),
    }
    write_parquet(fit.coefficients, OUT_FIT, metadata=fit_metadata)
    # Drop the float helper col before writing parquet — Decimal is canonical.
    pred_df = fit.per_parcel_predictions[
        ["pams_pin", "estimated_true_value", "neighborhood_fe", "residual"]
    ].copy()
    write_parquet(pred_df, OUT_PREDS, metadata=fit_metadata)

    # ---- Per-PIN overlay JSON (atomic) ----------------------------------
    overlay = {
        str(row["pams_pin"]): {
            "estimated_true_value": str(row["estimated_true_value"]),
            "estimated_true_value_float": float(row["estimated_true_value_float"]),
            "neighborhood_fe": int(row["neighborhood_fe"]),
        }
        for _, row in fit.per_parcel_predictions.iterrows()
    }
    atomic_write_json(OUT_OVERLAY, overlay)

    # ---- Vega-Lite chart specs (atomic) ---------------------------------
    _save_altair_chart_atomically(coefficient_chart(fit), OUT_COEF_CHART)
    _save_altair_chart_atomically(residual_chart(fit), OUT_RESID_CHART)
    atomic_write_json(OUT_CHORO_CHART, choropleth_chart_spec(fit.per_parcel_predictions))

    # ---- R² gate --------------------------------------------------------
    r2_target = float(constants.HEDONIC_R2_TARGET)
    if fit.r_squared < 0.5:
        print(
            f"FAIL: catastrophic R²={fit.r_squared:.4f} (< 0.5 floor). "
            f"Hedonic is not usable downstream. Investigate data/spec.",
            file=sys.stderr,
        )
        return 1
    if fit.r_squared < r2_target:
        print(
            f"WARN: R²={fit.r_squared:.4f} below MODEL-02 target "
            f"({r2_target}). Project pre-commits to publish either result; "
            f"continuing with documented gap.",
            file=sys.stderr,
        )

    # ---- Aggregate sanity (MODEL-03 §3) ---------------------------------
    total = sum(float(v) for v in fit.per_parcel_predictions["estimated_true_value_float"])
    target = float(constants.EXPECTED_AGGREGATE_ASSESSED)
    pct = abs(total - target) / target if target else 0.0
    print(
        f"Σ estimated_true_value = ${total:,.0f}; "
        f"target ${target:,.0f}; pct_off={pct:.4%} "
        f"(calibration_factor applied = {fit.calibration_factor:.4f})"
    )
    print(f"Wrote {len(fit.per_parcel_predictions)} predictions → {OUT_PREDS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
