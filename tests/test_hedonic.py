"""Phase 2 Plan 04 — hedonic OLS module tests.

Synthetic-fixture pattern mirrors `tests/test_validate_checks.py`:
build small in-memory parquets, call `fit_hedonic` end-to-end, assert
shapes, determinism, and Duan's-smearing / calibration mechanics.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point

from fairhaven_tax import constants
from fairhaven_tax.models import hedonic as hed


# ---------------------------------------------------------------------------
# Synthetic fixtures
# ---------------------------------------------------------------------------


def _synthetic_parcels(n_parcels: int = 80, seed: int = 42) -> gpd.GeoDataFrame:
    """Build n_parcels with random NJ-State-Plane-ish coords and PINs."""
    rng = np.random.default_rng(seed)
    xs = rng.uniform(580_000, 590_000, n_parcels)
    ys = rng.uniform(540_000, 550_000, n_parcels)
    pins = [f"1314_{i // 10}_{i % 10 + 1}" for i in range(n_parcels)]
    geom = [Point(x, y) for x, y in zip(xs, ys)]
    return gpd.GeoDataFrame(
        {"pams_pin": pins, "property_class": ["2"] * n_parcels},
        geometry=geom,
        crs="EPSG:3424",
    )


def _synthetic_prc(parcels_gdf: gpd.GeoDataFrame, seed: int = 42) -> pd.DataFrame:
    """Build a synthetic prc.parquet matching the real D-32 schema columns."""
    rng = np.random.default_rng(seed)
    n = len(parcels_gdf)
    livable = rng.uniform(1200, 3500, n)
    acreage = rng.uniform(0.10, 0.50, n)
    year_built = rng.integers(1920, 2010, n).astype(float)
    eff_age = rng.integers(5, 60, n).astype(float)
    bedrooms = rng.integers(2, 6, n).astype(float)
    bathrooms = rng.integers(1, 5, n).astype(float)
    conditions = rng.choice(["FAIR", "NORMAL", "GOOD"], n)
    quality = rng.choice(["17", "19", "21"], n)
    return pd.DataFrame({
        "pams_pin": parcels_gdf["pams_pin"].astype(str).to_numpy(),
        "livable_area": [Decimal(str(int(v))) for v in livable],
        "acreage": [Decimal(str(round(v, 4))) for v in acreage],
        "year_built": year_built,
        "eff_age": eff_age,
        "notice_year": np.full(n, 2026),
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "condition": conditions,
        "quality_grade": quality,
        "current_year_assessment": [Decimal(str(int(v))) for v in rng.uniform(500_000, 2_000_000, n)],
    })


def _synthetic_sales(
    prc_df: pd.DataFrame,
    n_sales: int = 50,
    seed: int = 42,
    noise_sigma: float = 0.18,
) -> pd.DataFrame:
    """Build synthetic sales whose log-prices follow a known-coefficient hedonic.

    True DGP:
       log(price) = 6.0 + 0.55*log(livable) + 0.18*log(acreage)
                  + 0.004*effective_build_year
                  + 0.04*bedrooms + 0.06*bathrooms
                  + 0.05*condition_ord + 0.04*quality_grade_ord/20
                  + N(0, noise_sigma)
    """
    rng = np.random.default_rng(seed)
    sample = prc_df.sample(n=n_sales, random_state=seed).reset_index(drop=True)
    livable = sample["livable_area"].map(float).to_numpy()
    acreage = sample["acreage"].map(float).to_numpy()
    eff_year = (sample["notice_year"].astype(float) - sample["eff_age"].astype(float)).to_numpy()
    bedrooms = sample["bedrooms"].astype(float).to_numpy()
    bathrooms = sample["bathrooms"].astype(float).to_numpy()
    cond_map = {"POOR": 1, "FAIR": 2, "NORMAL": 3, "GOOD": 4, "EXCELLENT": 5}
    cond = np.array([cond_map[c] for c in sample["condition"].tolist()], dtype=float)
    qg = sample["quality_grade"].astype(int).to_numpy().astype(float)
    log_price = (
        6.0
        + 0.55 * np.log(livable)
        + 0.18 * np.log(acreage)
        + 0.004 * eff_year
        + 0.04 * bedrooms
        + 0.06 * bathrooms
        + 0.05 * cond
        + 0.04 * (qg / 20.0)
        + rng.normal(0, noise_sigma, n_sales)
    )
    prices = np.exp(log_price)
    sale_years = rng.integers(2020, 2026, n_sales)
    sale_dates = [pd.Timestamp(year=int(y), month=6, day=15).date() for y in sale_years]
    return pd.DataFrame({
        "parcel_pin": sample["pams_pin"].astype(str).to_numpy(),
        "sale_date": sale_dates,
        "sale_price": [Decimal(str(round(float(p), 2))) for p in prices],
        "nu_code": [""] * n_sales,
    })


def _write_fixtures(tmp_path: Path, *, seed: int = 42, n_parcels: int = 80, n_sales: int = 50):
    parcels = _synthetic_parcels(n_parcels=n_parcels, seed=seed)
    prc = _synthetic_prc(parcels, seed=seed)
    sales = _synthetic_sales(prc, n_sales=n_sales, seed=seed)
    parcels_path = tmp_path / "parcels.parquet"
    prc_path = tmp_path / "prc.parquet"
    sales_path = tmp_path / "sales.parquet"
    parcels.to_parquet(parcels_path)
    prc.to_parquet(prc_path)
    sales.to_parquet(sales_path)
    return parcels_path, prc_path, sales_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFit:
    def test_returns_dataclass_with_expected_shape(self, tmp_path):
        parcels, prc, sales = _write_fixtures(tmp_path)
        fit = hed.fit_hedonic(sales, prc, parcels, k_neighborhood=4, calibrate_to=None)
        # Coefficients DataFrame
        assert {"term", "estimate", "std_err_hc3", "ci_lo", "ci_hi", "p_value"}.issubset(
            fit.coefficients.columns
        )
        # Residuals DataFrame
        assert {"pams_pin", "sale_year", "predicted", "actual", "residual"}.issubset(
            fit.residuals.columns
        )
        # Per-parcel predictions for ALL parcels (after dropping missing-neighborhood)
        assert {"pams_pin", "estimated_true_value", "neighborhood_fe", "residual"}.issubset(
            fit.per_parcel_predictions.columns
        )
        # Cardinality: all parcels predicted
        assert len(fit.per_parcel_predictions) == 80
        # Reasonable R² on synthetic data with known DGP
        assert fit.r_squared > 0.6, f"R²={fit.r_squared}"
        assert fit.n_obs > 0

    def test_recovered_coefficients_close_to_truth(self, tmp_path):
        # Bigger sample for a tighter check.
        parcels, prc, sales = _write_fixtures(tmp_path, n_parcels=200, n_sales=120)
        fit = hed.fit_hedonic(sales, prc, parcels, k_neighborhood=4, calibrate_to=None)
        coef = fit.coefficients.set_index("term")["estimate"]
        # Synthetic DGP truth: log(livable) ≈ 0.55, log(lot_size) ≈ 0.18.
        assert 0.30 < coef["np.log(livable_area)"] < 0.80
        assert 0.05 < coef["np.log(lot_size_clipped)"] < 0.40


class TestDeterminism:
    def test_seed_determinism(self, tmp_path):
        parcels, prc, sales = _write_fixtures(tmp_path)
        fit1 = hed.fit_hedonic(sales, prc, parcels, seed=42, k_neighborhood=4, calibrate_to=None)
        fit2 = hed.fit_hedonic(sales, prc, parcels, seed=42, k_neighborhood=4, calibrate_to=None)
        # Identical neighborhood labels
        np.testing.assert_array_equal(
            fit1.per_parcel_predictions["neighborhood_fe"].to_numpy(),
            fit2.per_parcel_predictions["neighborhood_fe"].to_numpy(),
        )
        # Identical prediction floats
        np.testing.assert_array_equal(
            fit1.per_parcel_predictions["estimated_true_value_float"].to_numpy(),
            fit2.per_parcel_predictions["estimated_true_value_float"].to_numpy(),
        )

    def test_random_seed_constant_is_42(self):
        assert constants.RANDOM_SEED == 42


class TestEffectiveBuildYear:
    def test_effective_build_year_falls_back_to_year_built(self):
        prc = pd.DataFrame({
            "pams_pin": ["1314_1_1", "1314_1_2"],
            "livable_area": [Decimal("1500"), Decimal("1800")],
            "acreage": [Decimal("0.20"), Decimal("0.25")],
            "year_built": [1950.0, 1980.0],
            "eff_age": [None, 25.0],   # first row missing
            "notice_year": [2026, 2026],
            "bedrooms": [3, 4],
            "bathrooms": [2, 3],
            "condition": ["NORMAL", "GOOD"],
            "quality_grade": ["19", "21"],
        })
        out = hed._coerce_features(prc)
        # First row: eff_age missing → fallback to year_built (1950)
        assert out.loc[0, "effective_build_year"] == 1950.0
        # Second row: 2026 - 25 = 2001
        assert out.loc[1, "effective_build_year"] == 2001.0


class TestCalibration:
    def test_calibration_factor_one_when_within_tolerance(self):
        preds = np.array([100.0, 100.0, 100.0, 100.0])
        out, factor = hed._calibrate(preds, target=Decimal("400"), tolerance=Decimal("0.05"))
        assert factor == 1.0
        np.testing.assert_array_equal(out, preds)

    def test_calibration_applied_when_off(self):
        preds = np.array([100.0, 100.0, 100.0, 100.0])  # sum=400
        out, factor = hed._calibrate(preds, target=Decimal("800"), tolerance=Decimal("0.05"))
        assert factor == pytest.approx(2.0)
        assert float(np.sum(out)) == pytest.approx(800.0)


class TestSmearing:
    def test_duan_smearing_factor_is_at_least_one_in_practice(self, tmp_path):
        parcels, prc, sales = _write_fixtures(tmp_path)
        fit = hed.fit_hedonic(sales, prc, parcels, k_neighborhood=4, calibrate_to=None)
        # By Jensen's inequality, mean(exp(resid)) ≥ exp(mean(resid)) = ~1
        # for OLS residuals on a log-link model. Tolerate light numeric float noise.
        assert fit.smearing_factor >= 0.95


class TestChartSpecs:
    def test_chart_specs_emit_valid_vegalite_json(self, tmp_path):
        parcels, prc, sales = _write_fixtures(tmp_path)
        fit = hed.fit_hedonic(sales, prc, parcels, k_neighborhood=4, calibrate_to=None)

        # Altair charts → JSON-roundtrip validates schema & vega-lite shape.
        coef = hed.coefficient_chart(fit).to_dict()
        resid = hed.residual_chart(fit).to_dict()
        choro = hed.choropleth_chart_spec(fit.per_parcel_predictions)

        for name, spec in [("coef", coef), ("resid", resid), ("choro", choro)]:
            assert "$schema" in spec, name
            assert spec["$schema"].startswith("https://vega.github.io/schema/vega-lite/"), (
                f"{name}: {spec['$schema']}"
            )
            # Round-trip via JSON
            json.loads(json.dumps(spec, default=str))


class TestKSelection:
    def test_pick_best_k_returns_k_in_candidates(self, tmp_path):
        parcels, _, _ = _write_fixtures(tmp_path)
        gdf = gpd.read_parquet(parcels)
        best_k, _, _, sil_by_k = hed._pick_best_k(gdf, (5, 6, 7, 8), seed=42)
        assert best_k in (5, 6, 7, 8)
        assert set(sil_by_k.keys()) == {5, 6, 7, 8}
        # All silhouette scores well-defined for >1 cluster.
        for v in sil_by_k.values():
            assert -1.0 <= v <= 1.0
