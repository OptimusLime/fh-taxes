"""Hedonic OLS on 2020-2025 arms-length sales (D-50, D-51, D-52, D-54).

Spec sourced from .planning/phases/02-statistical-pipeline/02-RESEARCH.md §1.5
(Berry/Cook County replication) with one project-specific update:

    log(sale_price) ~ log(livable_area) + log(lot_size_clipped)
                    + effective_build_year
                    + bedrooms + bathrooms + condition_ord + quality_grade_ord
                    + C(neighborhood_fe) + C(sale_year)

Renovation handling (D-supplemental, Phase 1.5 follow-up):
    effective_build_year = notice_year - eff_age   (when eff_age non-null)
                         |  year_built              (fallback)

`eff_age` is the assessor's own depreciation-curve estimate that embeds
renovation history; using it directly here pulls the renovation signal into
the hedonic without re-deriving it. The renovation overlay (built by
`scripts/derive_renovation_events.py`) is diagnostic ONLY — it is NOT used
as a regressor here.

K-means neighborhood FE (MODEL-01):
    Cluster parcel centroids (EPSG:3424 → standard-scaled lat/lon)
    with `KMeans(n_clusters=k, random_state=constants.RANDOM_SEED, n_init=10)`.
    Default k = HEDONIC_K_NEIGHBORHOOD_DEFAULT = 6; `fit_hedonic` evaluates
    {5, 6, 7, 8} and picks the k with the highest mean silhouette score.

Robust SEs: `OLS(...).fit(cov_type='HC3')` per RESEARCH.md §1.5 / §6.

Per-parcel prediction (MODEL-02 + MODEL-03):
    After fitting on the sales sample, the model is applied to ALL ~2,060
    class-2 parcels. Missing categorical/integer features are imputed with
    within-neighborhood medians (or sample-wide median fallback).
    Predictions are exponentiated and corrected with Duan's smearing
    factor for log-link retransformation bias.

Calibration: if Σ predicted_value deviates >5% from
    constants.EXPECTED_AGGREGATE_ASSESSED ($2.74B), all predictions are
    scaled by a single multiplicative constant. The factor (1.0 if not
    applied) is recorded in the returned dataclass and surfaced in the
    output parquet metadata. MODEL-03 explicitly permits this.

This module is pure-function: it returns DataFrames + Altair Charts; the
caller (`scripts/run_hedonic.py`) handles parquet/JSON writes.
"""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import altair as alt
import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from fairhaven_tax import constants

# ---------------------------------------------------------------------------
# Categorical encodings (RESEARCH.md §1.5: encode as integer 1..5)
# ---------------------------------------------------------------------------

# `condition` arrives as e.g. "NORMAL", "GOOD", "FAIR", "POOR" (sometimes with
# a suffix " A"/" B"/" C"/" DECK" — strip and use the first token).
_CONDITION_ORD: dict[str, int] = {
    "POOR": 1,
    "FAIR": 2,
    "NORMAL": 3,
    "GOOD": 4,
    "EXCELLENT": 5,
}

# `quality_grade` arrives as numeric strings ("17", "21", ...). Source value
# "SOURCE" is a sentinel for "feed not parsed" → treat as missing.
def _parse_quality_grade(v: Any) -> float:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return np.nan
    s = str(v).strip()
    if not s or s.upper() == "SOURCE":
        return np.nan
    try:
        return float(int(s))
    except (TypeError, ValueError):
        return np.nan


def _parse_condition(v: Any) -> float:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return np.nan
    head = str(v).strip().split()[0].upper() if str(v).strip() else ""
    return float(_CONDITION_ORD.get(head, np.nan))


def _to_float(v: Any) -> float:
    if v is None:
        return np.nan
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, float) and np.isnan(v):
        return np.nan
    try:
        return float(v)
    except (TypeError, ValueError):
        return np.nan


def _to_decimal(f: float, places: int = 2) -> Decimal | None:
    if f is None or (isinstance(f, float) and np.isnan(f)):
        return None
    q = Decimal(10) ** -places
    return Decimal(str(round(float(f), places))).quantize(q)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Smallest non-condo lot we will model honestly; below this, log(acreage)
# explodes. 0.01 acre ≈ 435 sq ft (smaller than any real Fair Haven lot;
# class-2 condo PINs use this floor).
_ACREAGE_FLOOR: float = 0.01

# Hedonic formula. statsmodels parses `np.log` and `C(...)` from `formula.api.ols`.
HEDONIC_FORMULA: str = (
    "np.log(sale_price) ~ "
    "np.log(livable_area) + np.log(lot_size_clipped) "
    "+ effective_build_year "
    "+ bedrooms + bathrooms + condition_ord + quality_grade_ord "
    "+ C(neighborhood_fe) + C(sale_year)"
)

_K_CANDIDATES: tuple[int, ...] = (5, 6, 7, 8)


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class HedonicFit:
    coefficients: pd.DataFrame
    residuals: pd.DataFrame
    per_parcel_predictions: pd.DataFrame
    r_squared: float
    adj_r_squared: float
    n_obs: int
    n_params: int
    k_neighborhood: int
    silhouette_score: float
    seed: int
    calibration_factor: float
    smearing_factor: float
    feature_summary: dict[str, Any] = field(default_factory=dict)
    model: Any = None  # statsmodels result; not serialised


# ---------------------------------------------------------------------------
# Feature engineering (pure)
# ---------------------------------------------------------------------------


def _coerce_features(prc_df: pd.DataFrame) -> pd.DataFrame:
    """Cast prc.parquet's heterogenous columns into hedonic-ready floats.

    Returns a DataFrame indexed by `pams_pin` with columns:
      livable_area, acreage, lot_size_clipped, year_built, eff_age,
      notice_year, effective_build_year, bedrooms, bathrooms,
      condition_ord, quality_grade_ord
    """
    df = pd.DataFrame({"pams_pin": prc_df["pams_pin"].astype(str)})
    df["livable_area"] = prc_df["livable_area"].map(_to_float)
    # livable_area=0 → NaN so within-neighborhood median imputation fills it.
    # Class-2 parcels with literal 0 livable_area are MOD-IV vacant-lot or
    # data-quality artifacts; treating them as missing is the right call.
    df.loc[df["livable_area"] <= 0, "livable_area"] = np.nan
    df["acreage"] = prc_df["acreage"].map(_to_float)
    df["lot_size_clipped"] = df["acreage"].fillna(_ACREAGE_FLOOR).clip(lower=_ACREAGE_FLOOR)
    df["year_built"] = pd.to_numeric(prc_df["year_built"], errors="coerce")
    df["eff_age"] = pd.to_numeric(prc_df["eff_age"], errors="coerce")
    df["notice_year"] = pd.to_numeric(prc_df["notice_year"], errors="coerce")
    # effective_build_year = notice_year - eff_age, fallback to year_built
    eff_year = df["notice_year"] - df["eff_age"]
    df["effective_build_year"] = eff_year.where(eff_year.notna(), df["year_built"])
    df["bedrooms"] = pd.to_numeric(prc_df["bedrooms"], errors="coerce")
    df["bathrooms"] = pd.to_numeric(prc_df["bathrooms"], errors="coerce")
    df["condition_ord"] = prc_df["condition"].map(_parse_condition)
    df["quality_grade_ord"] = prc_df["quality_grade"].map(_parse_quality_grade)
    return df


# ---------------------------------------------------------------------------
# Neighborhood FE via k-means (MODEL-01)
# ---------------------------------------------------------------------------


def _assign_neighborhoods(
    parcels_gdf: gpd.GeoDataFrame,
    k: int,
    seed: int,
) -> tuple[pd.DataFrame, float]:
    """Cluster parcel centroids into `k` neighborhoods.

    Returns (DataFrame[pams_pin, neighborhood_fe], silhouette_score).
    Centroids are computed in the gdf's native CRS (EPSG:3424 ftUS for
    NJ State Plane); coordinates are StandardScaled before KMeans.
    """
    if parcels_gdf.crs is None:
        raise ValueError("parcels_gdf has no CRS; cannot compute centroids")
    # Suppress GeoPandas "centroid in geographic CRS" warning — we are in
    # projected NJ State Plane, so this is a non-issue.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cents = parcels_gdf.geometry.centroid
    pins = parcels_gdf["pams_pin"].astype(str).tolist()
    coords = np.column_stack([cents.x.to_numpy(), cents.y.to_numpy()])
    scaler = StandardScaler()
    coords_s = scaler.fit_transform(coords)
    km = KMeans(n_clusters=k, random_state=seed, n_init=10)
    labels = km.fit_predict(coords_s)
    sil = float(silhouette_score(coords_s, labels)) if k > 1 and len(set(labels)) > 1 else 0.0
    out = pd.DataFrame({"pams_pin": pins, "neighborhood_fe": labels.astype(int)})
    return out, sil


def _pick_best_k(
    parcels_gdf: gpd.GeoDataFrame,
    candidates: tuple[int, ...],
    seed: int,
) -> tuple[int, pd.DataFrame, float, dict[int, float]]:
    """Try each `k` in `candidates`; return the k with max silhouette."""
    best_k = candidates[0]
    best_df = None
    best_sil = -np.inf
    sil_by_k: dict[int, float] = {}
    for k in candidates:
        df, sil = _assign_neighborhoods(parcels_gdf, k, seed)
        sil_by_k[k] = sil
        if sil > best_sil:
            best_sil = sil
            best_k = k
            best_df = df
    assert best_df is not None
    return best_k, best_df, best_sil, sil_by_k


# ---------------------------------------------------------------------------
# Imputation for unsold-parcel prediction (MODEL-03)
# ---------------------------------------------------------------------------


_HEDONIC_NUMERIC_COLS: tuple[str, ...] = (
    "livable_area",
    "lot_size_clipped",
    "effective_build_year",
    "bedrooms",
    "bathrooms",
    "condition_ord",
    "quality_grade_ord",
)


def _impute_within_neighborhood(
    df: pd.DataFrame,
    feature_cols: tuple[str, ...],
    neighborhood_col: str = "neighborhood_fe",
) -> pd.DataFrame:
    """Fill NaN per (neighborhood, feature) with within-neighborhood median;
    fall back to sample-wide median if a neighborhood has no observed value.
    """
    df = df.copy()
    overall = {c: df[c].median(skipna=True) for c in feature_cols}
    for c in feature_cols:
        # Within-neighborhood median
        df[c] = df.groupby(neighborhood_col)[c].transform(
            lambda s: s.fillna(s.median())
        )
        # Sample-wide fallback
        df[c] = df[c].fillna(overall[c])
    return df


# ---------------------------------------------------------------------------
# Calibration (MODEL-03)
# ---------------------------------------------------------------------------


def _calibrate(
    predictions: np.ndarray,
    target: Decimal = constants.EXPECTED_AGGREGATE_ASSESSED,
    tolerance: Decimal = Decimal("0.05"),
) -> tuple[np.ndarray, float]:
    """Scale predictions if Σ predictions strays >5% from `target`.

    Returns (calibrated_predictions, calibration_factor).  Factor=1.0 if no
    calibration applied.
    """
    target_f = float(target)
    total = float(np.nansum(predictions))
    if target_f == 0 or total == 0:
        return predictions, 1.0
    pct_off = abs(total - target_f) / target_f
    if pct_off <= float(tolerance):
        return predictions, 1.0
    factor = target_f / total
    return predictions * factor, float(factor)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fit_hedonic(
    sales_path: Path | str,
    prc_path: Path | str,
    parcels_path: Path | str,
    *,
    seed: int = constants.RANDOM_SEED,
    k_neighborhood: int | None = constants.HEDONIC_K_NEIGHBORHOOD_DEFAULT,
    train_year_min: int = constants.HEDONIC_TRAIN_YEAR_MIN,
    train_year_max: int = constants.HEDONIC_TRAIN_YEAR_MAX,
    arms_length_nu_codes: frozenset[str] = constants.ARMS_LENGTH_NU_CODES,
    calibrate_to: Decimal | None = constants.EXPECTED_AGGREGATE_ASSESSED,
    k_candidates: tuple[int, ...] = _K_CANDIDATES,
) -> HedonicFit:
    """Fit Berry-style hedonic and predict for all class-2 parcels.

    If `k_neighborhood is None`, evaluate `k_candidates` and pick max-silhouette.

    The fit uses statsmodels `OLS(...).fit(cov_type='HC3')`. Categorical
    fixed effects (neighborhood_fe, sale_year) are encoded via patsy `C(...)`.
    """
    sales_df = pd.read_parquet(sales_path)
    prc_df = pd.read_parquet(prc_path)
    parcels_gdf = gpd.read_parquet(parcels_path)

    # ---- 1. Neighborhood FE (k chosen on parcels universe) -----
    if k_neighborhood is None:
        k_used, neigh_df, sil, sil_by_k = _pick_best_k(parcels_gdf, k_candidates, seed)
    else:
        neigh_df, sil = _assign_neighborhoods(parcels_gdf, k_neighborhood, seed)
        k_used = k_neighborhood
        sil_by_k = {k_neighborhood: sil}

    # ---- 2. Build prc feature frame and join neighborhoods --------
    prc_features = _coerce_features(prc_df).merge(neigh_df, on="pams_pin", how="left")

    # ---- 3. Build training frame ------------------------------------
    sales = sales_df.copy()
    sales["pams_pin"] = sales["parcel_pin"].astype(str)
    sales["sale_price"] = sales["sale_price"].map(_to_float)
    sales["sale_year"] = pd.to_datetime(sales["sale_date"], errors="coerce").dt.year.astype("Int64")
    nu_norm = sales["nu_code"].fillna("").astype(str).str.strip()
    arms = nu_norm.isin(arms_length_nu_codes)
    in_window = (sales["sale_year"] >= train_year_min) & (sales["sale_year"] <= train_year_max)
    train = sales.loc[arms & in_window, ["pams_pin", "sale_year", "sale_price"]].copy()
    train = train.merge(prc_features, on="pams_pin", how="left")
    # Required-feature completeness
    required = list(_HEDONIC_NUMERIC_COLS) + ["neighborhood_fe", "sale_year", "sale_price"]
    train_clean = train.dropna(subset=required).copy()
    train_clean["sale_year"] = train_clean["sale_year"].astype(int)
    train_clean["neighborhood_fe"] = train_clean["neighborhood_fe"].astype(int)
    n_obs = len(train_clean)
    if n_obs == 0:
        raise ValueError(
            "fit_hedonic: zero rows survived the arms-length + window + "
            "feature-completeness filter — refusing to fit"
        )

    # ---- 4. Fit OLS with HC3 robust SEs ------------------------------
    model = smf.ols(formula=HEDONIC_FORMULA, data=train_clean).fit(cov_type="HC3")
    n_params = int(model.df_model) + 1  # +1 for intercept

    # ---- 5. Coefficients table ---------------------------------------
    params = model.params
    bse = model.bse
    pvalues = model.pvalues
    conf_int = model.conf_int(alpha=0.05)
    coef_rows = []
    for term in params.index:
        coef_rows.append({
            "term": str(term),
            "estimate": float(params[term]),
            "std_err_hc3": float(bse[term]),
            "p_value": float(pvalues[term]),
            "ci_lo": float(conf_int.loc[term, 0]),
            "ci_hi": float(conf_int.loc[term, 1]),
        })
    coef_df = pd.DataFrame(coef_rows)

    # ---- 6. Training residuals & Duan's smearing -------------------
    log_pred = model.fittedvalues
    log_actual = np.log(train_clean["sale_price"].astype(float).to_numpy())
    log_resid = log_actual - log_pred.to_numpy()
    smearing = float(np.mean(np.exp(log_resid)))
    resid_df = pd.DataFrame({
        "pams_pin": train_clean["pams_pin"].astype(str).to_numpy(),
        "sale_year": train_clean["sale_year"].astype(int).to_numpy(),
        "predicted": np.exp(log_pred.to_numpy()) * smearing,
        "actual": train_clean["sale_price"].astype(float).to_numpy(),
        "residual": np.exp(log_pred.to_numpy()) * smearing
                    - train_clean["sale_price"].astype(float).to_numpy(),
    })

    # ---- 7. Predict for all 2,060 parcels ---------------------------
    universe = prc_features.copy()
    # Drop rows w/o a neighborhood (parcel without geometry, edge case).
    universe = universe.dropna(subset=["neighborhood_fe"]).copy()
    universe["neighborhood_fe"] = universe["neighborhood_fe"].astype(int)
    universe = _impute_within_neighborhood(universe, _HEDONIC_NUMERIC_COLS)
    # Use the modal in-window sale_year for prediction so the year-FE term
    # is anchored — pick the most recent year that exists in training.
    pred_year = int(train_clean["sale_year"].max())
    universe["sale_year"] = pred_year
    log_pred_universe = model.predict(universe)
    pred_values = np.exp(log_pred_universe.to_numpy()) * smearing
    # Calibrate (MODEL-03)
    if calibrate_to is not None:
        pred_values, cal_factor = _calibrate(pred_values, target=calibrate_to)
    else:
        cal_factor = 1.0
    # Per-parcel residual: only defined for sold parcels (training set).
    sold_resid = dict(zip(
        resid_df["pams_pin"].astype(str),
        (resid_df["actual"] - resid_df["predicted"]).astype(float),
    ))
    universe_residuals = universe["pams_pin"].astype(str).map(sold_resid)
    pred_df = pd.DataFrame({
        "pams_pin": universe["pams_pin"].astype(str).to_numpy(),
        "estimated_true_value": [_to_decimal(v) for v in pred_values],
        "estimated_true_value_float": pred_values,
        "neighborhood_fe": universe["neighborhood_fe"].astype(int).to_numpy(),
        "residual": universe_residuals.to_numpy(),
    })

    feature_summary = {
        "n_sales_input": int(len(sales_df)),
        "n_after_arms_length_filter": int(arms.sum()),
        "n_after_year_window": int((arms & in_window).sum()),
        "n_after_feature_completeness": int(n_obs),
        "obs_per_param": float(n_obs) / float(n_params) if n_params else None,
        "k_silhouette_by_k": sil_by_k,
        "pred_year_used": pred_year,
        "n_parcels_predicted": int(len(pred_df)),
        "n_acreage_clipped": int((prc_features["acreage"].fillna(0) <= _ACREAGE_FLOOR).sum()),
    }

    return HedonicFit(
        coefficients=coef_df,
        residuals=resid_df,
        per_parcel_predictions=pred_df,
        r_squared=float(model.rsquared),
        adj_r_squared=float(model.rsquared_adj),
        n_obs=n_obs,
        n_params=n_params,
        k_neighborhood=int(k_used),
        silhouette_score=float(sil_by_k[k_used]),
        seed=int(seed),
        calibration_factor=float(cal_factor),
        smearing_factor=float(smearing),
        feature_summary=feature_summary,
        model=model,
    )


# ---------------------------------------------------------------------------
# Charts (D-61, D-62)
# ---------------------------------------------------------------------------


def coefficient_chart(fit: HedonicFit) -> alt.Chart:
    """Coefficient + 95% CI bar chart (HC3 SEs).

    The intercept is excluded from the visualization (it dominates the
    y-axis and isn't substantively interesting).
    """
    df = fit.coefficients[fit.coefficients["term"] != "Intercept"].copy()
    df["term_short"] = df["term"].str.replace(r"^C\(([^)]+)\)\[(?:T\.)?", r"\1=", regex=True)
    df["term_short"] = df["term_short"].str.replace(r"\]$", "", regex=True)
    base = alt.Chart(df).encode(
        y=alt.Y("term_short:N", sort="-x", title="Coefficient"),
    )
    pts = base.mark_point(filled=True, size=70, color="#1a56db").encode(
        x=alt.X("estimate:Q", title="Estimate (95% CI, HC3 robust SEs)"),
        tooltip=[
            alt.Tooltip("term_short:N", title="term"),
            alt.Tooltip("estimate:Q", format=".4f"),
            alt.Tooltip("std_err_hc3:Q", format=".4f"),
            alt.Tooltip("ci_lo:Q", format=".4f"),
            alt.Tooltip("ci_hi:Q", format=".4f"),
            alt.Tooltip("p_value:Q", format=".4g"),
        ],
    )
    err = base.mark_rule(color="#1a56db").encode(
        x="ci_lo:Q",
        x2="ci_hi:Q",
    )
    zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#999", strokeDash=[4, 3]).encode(x="x:Q")
    return (zero + err + pts).properties(
        title=f"Hedonic coefficients (95% CI; n={fit.n_obs}, R²={fit.r_squared:.3f})",
        width=600,
        height=max(300, 22 * len(df)),
    )


def residual_chart(fit: HedonicFit) -> alt.Chart:
    """Predicted-vs-actual scatter with 45° reference line (training sample)."""
    df = fit.residuals.copy()
    if len(df) == 0:
        return alt.Chart(pd.DataFrame({"x": [], "y": []})).mark_point().properties(
            title="No residuals (empty training sample)",
        )
    lo = float(min(df["predicted"].min(), df["actual"].min()))
    hi = float(max(df["predicted"].max(), df["actual"].max()))
    pts = alt.Chart(df).mark_circle(size=60, opacity=0.55, color="#1a56db").encode(
        x=alt.X("predicted:Q", title="Predicted sale price ($)", axis=alt.Axis(format="$,.0f")),
        y=alt.Y("actual:Q", title="Actual sale price ($)", axis=alt.Axis(format="$,.0f")),
        tooltip=[
            alt.Tooltip("pams_pin:N", title="pin"),
            alt.Tooltip("sale_year:O"),
            alt.Tooltip("predicted:Q", format="$,.0f"),
            alt.Tooltip("actual:Q", format="$,.0f"),
            alt.Tooltip("residual:Q", format="$,.0f"),
        ],
    )
    line = alt.Chart(pd.DataFrame({"x": [lo, hi], "y": [lo, hi]})).mark_line(
        color="#888", strokeDash=[4, 3]
    ).encode(x="x:Q", y="y:Q")
    return (line + pts).properties(
        title=(
            f"Predicted vs actual (n={len(df)}, R²={fit.r_squared:.3f}, "
            f"Duan's smearing={fit.smearing_factor:.3f})"
        ),
        width=560,
        height=420,
    )


def choropleth_chart_spec(
    predictions: pd.DataFrame,
    parcels_geojson_url: str = "/data/parcels.geojson",
    overlay_url: str = "/data/overlays/estimated_true_value.json",
) -> dict:
    """Vega-Lite choropleth spec consuming parcels.geojson + lookup overlay.

    URL-referenced (not inline) per the Vega-Lite 5000-row inline limit
    flagged in RESEARCH.md. Altair's geo support is TopoJSON-only, so we
    hand-author the spec.
    """
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": "Hedonic estimated true value (predicted, $)",
        "width": 720,
        "height": 560,
        "data": {
            "url": parcels_geojson_url,
            "format": {"type": "json", "property": "features"},
        },
        "transform": [
            {
                "lookup": "properties.pams_pin",
                "from": {
                    "data": {"url": overlay_url},
                    "key": "pams_pin",
                    "fields": ["estimated_true_value_float"],
                },
                "as": ["estimated_true_value"],
            }
        ],
        "projection": {"type": "mercator"},
        "mark": {"type": "geoshape", "stroke": "#fff", "strokeWidth": 0.3},
        "encoding": {
            "color": {
                "field": "estimated_true_value",
                "type": "quantitative",
                "scale": {"scheme": "viridis", "type": "quantile"},
                "legend": {"title": "estimated_true_value", "format": "$,.0f"},
            },
            "tooltip": [
                {"field": "properties.pams_pin", "type": "nominal", "title": "pin"},
                {
                    "field": "estimated_true_value",
                    "type": "quantitative",
                    "format": "$,.0f",
                    "title": "predicted",
                },
            ],
        },
    }


__all__ = [
    "HEDONIC_FORMULA",
    "HedonicFit",
    "coefficient_chart",
    "fit_hedonic",
    "residual_chart",
    "choropleth_chart_spec",
]
