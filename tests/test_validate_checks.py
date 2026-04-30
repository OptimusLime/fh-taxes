"""Phase 2 validation-checks tests (Plan 02-01).

Three test classes:
  * TestPrep            — Wave-0 prep (constants, atomic_write_json, altair import)
  * TestHistoricalRates — best-effort historical tax-rate dict (issue #3a)
  * TestPhase2Gates     — synthetic-fixture coverage of each Phase-2 gate
                          plus a subprocess test on scripts/run_validation.py
  * TestDataQualityViz  — end-to-end test for scripts/build_data_quality_viz.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from fairhaven_tax import constants
from fairhaven_tax.persist.json_io import atomic_write_json


# ---------------------------------------------------------------------------
# Task 1 — Wave-0 prep
# ---------------------------------------------------------------------------


class TestPrep:
    def test_random_seed_is_42(self):
        assert constants.RANDOM_SEED == 42

    def test_atomic_write_json_round_trips_and_leaves_no_tmp(self, tmp_path):
        path = tmp_path / "out" / "demo.json"
        payload = {"a": 1, "decimal": Decimal("1.427"), "nested": {"b": [1, 2, 3]}}
        atomic_write_json(path, payload)

        # File exists with parsed content.
        assert path.exists()
        loaded = json.loads(path.read_text())
        assert loaded["a"] == 1
        assert loaded["decimal"] == "1.427"  # Decimal -> str via default=str
        assert loaded["nested"]["b"] == [1, 2, 3]

        # No .tmp sibling left behind.
        assert not (path.parent / "demo.json.tmp").exists()
        siblings = [p.name for p in path.parent.iterdir() if p.name.endswith(".tmp")]
        assert siblings == []

    def test_altair_imports(self):
        import altair  # noqa: F401

    def test_iaao_thresholds_exact_values(self):
        assert constants.IAAO_COD_RESIDENTIAL_MAX == Decimal("15.0")
        assert constants.IAAO_PRD_MIN == Decimal("0.98")
        assert constants.IAAO_PRD_MAX == Decimal("1.03")
        assert constants.IAAO_PRB_MIN == Decimal("-0.05")
        assert constants.IAAO_PRB_MAX == Decimal("0.05")

    def test_hedonic_constants(self):
        assert constants.HEDONIC_TRAIN_YEAR_MIN == 2020
        assert constants.HEDONIC_TRAIN_YEAR_MAX == 2025
        assert constants.HEDONIC_K_NEIGHBORHOOD_DEFAULT == 6

    def test_cdf_constants(self):
        assert constants.CDF_GAP_BOUNDS == (Decimal("0.98"), Decimal("1.02"))
        assert constants.CDF_GAP_THRESHOLD == Decimal("0.03")
        assert constants.CDF_TEST_YEAR_MIN == 2014
        assert constants.CDF_TEST_YEAR_MAX == 2025


# ---------------------------------------------------------------------------
# Task 1 (2b) — Historical tax-rate dict
# ---------------------------------------------------------------------------


class TestHistoricalRates:
    def test_2025_rate_verified(self):
        assert constants.HISTORICAL_TAX_RATES[2025] == Decimal("1.427")

    def test_fallback_matches_2025(self):
        assert constants.HISTORICAL_TAX_RATES_FALLBACK == Decimal("1.427")

    def test_dict_well_formed_for_phase2_window(self):
        """Each year in 2020..2025 either has an explicit rate or the
        fallback is wired up — i.e. the dict is well-formed, not that
        every year is present."""
        for year in range(2020, 2026):
            rate = constants.HISTORICAL_TAX_RATES.get(
                year, constants.HISTORICAL_TAX_RATES_FALLBACK
            )
            assert isinstance(rate, Decimal)
            assert rate > 0


# ---------------------------------------------------------------------------
# Task 2 — Phase-2 gates
# ---------------------------------------------------------------------------


def _prc(
    n: int = 2060,
    *,
    null_share: float = 0.0,
    negative_assessment: bool = False,
    pin_prefix: str = "1314_10_",
) -> pd.DataFrame:
    """Synthetic prc frame matching the real D-32 schema."""
    pins = [f"{pin_prefix}{i}" for i in range(n)]
    n_null = int(n * null_share)

    def col(default):
        return [None] * n_null + [default] * (n - n_null)

    df = pd.DataFrame({
        "pams_pin": pins,
        "livable_area": col(1800.0),
        "bedrooms": col(3),
        "bathrooms": col(2.0),
        "condition": col("AVG"),
        "quality_grade": col("C"),
        "year_built": col(1955),
        "acreage": col(0.25),  # plan called this lot_size_acres; real schema = acreage
        "current_year_assessment": [Decimal("500000")] * n,
    })
    if negative_assessment and n > 0:
        df.loc[0, "current_year_assessment"] = Decimal("-1")
    return df


def _sales(n: int = 197, *, year: int = 2022, pin_prefix: str = "1314_10_") -> pd.DataFrame:
    return pd.DataFrame({
        "parcel_pin": [f"{pin_prefix}{i}" for i in range(n)],
        "sale_year": [year] * n,
        "sale_price": [Decimal("700000")] * n,
    })


def _modiv(
    n: int = 200,
    *,
    year: int = 2020,
    fill_sale: bool = True,
    pin_prefix: str = "1314_10_",
) -> pd.DataFrame:
    return pd.DataFrame({
        "parcel_pin": [f"{pin_prefix}{i}" for i in range(n)],
        "year": [year] * n,
        "sale_price": [Decimal("700000") if fill_sale else None] * n,
        "sale_assessment": [Decimal("400000") if fill_sale else None] * n,
    })


class TestPhase2Gates:
    def test_prc_required_features_pass(self):
        from fairhaven_tax.validate.checks import validate_prc_required_features
        r = validate_prc_required_features(_prc(2060, null_share=0.02))
        assert r.passed is True

    def test_prc_required_features_fail(self):
        from fairhaven_tax.validate.checks import validate_prc_required_features
        r = validate_prc_required_features(_prc(2060, null_share=0.5))
        assert r.passed is False
        assert "livable_area" in r.message or "non-null" in r.message

    def test_prc_row_count_pass(self):
        from fairhaven_tax.validate.checks import validate_prc_row_count
        assert validate_prc_row_count(_prc(2060)).passed is True

    def test_prc_row_count_fail_outside_5pct(self):
        from fairhaven_tax.validate.checks import validate_prc_row_count
        assert validate_prc_row_count(_prc(3000)).passed is False

    def test_sales_row_count_pass(self):
        from fairhaven_tax.validate.checks import validate_sales_row_count
        assert validate_sales_row_count(_sales(150)).passed is True

    def test_sales_row_count_fail(self):
        from fairhaven_tax.validate.checks import validate_sales_row_count
        assert validate_sales_row_count(_sales(50)).passed is False

    def test_sales_year_range_pass(self):
        from fairhaven_tax.validate.checks import validate_sales_year_range
        df = _sales(100, year=2022)
        df.loc[0, "sale_year"] = 2020
        df.loc[1, "sale_year"] = 2025
        assert validate_sales_year_range(df).passed is True

    def test_sales_year_range_fail(self):
        from fairhaven_tax.validate.checks import validate_sales_year_range
        df = _sales(100, year=2022)
        df.loc[0, "sale_year"] = 2019
        assert validate_sales_year_range(df).passed is False

    def test_modiv_history_sale_assessment_pass(self):
        from fairhaven_tax.validate.checks import validate_modiv_history_sale_assessment
        # 100 rows in 2020 with both filled -> ≥ 30
        df = _modiv(100, year=2020, fill_sale=True)
        assert validate_modiv_history_sale_assessment(df).passed is True

    def test_modiv_history_sale_assessment_fail(self):
        from fairhaven_tax.validate.checks import validate_modiv_history_sale_assessment
        # All in 2010 (pre-ADP) -> 0 in window
        df = _modiv(100, year=2010, fill_sale=True)
        assert validate_modiv_history_sale_assessment(df).passed is False

    def test_cross_source_pin_alignment_pass(self):
        from fairhaven_tax.validate.checks import validate_cross_source_pin_alignment
        prc = _prc(100, pin_prefix="1314_10_")
        sales = _sales(50, pin_prefix="1314_10_")
        modiv = _modiv(150, pin_prefix="1314_10_")
        assert validate_cross_source_pin_alignment(prc, sales, modiv).passed is True

    def test_cross_source_pin_alignment_fail(self):
        from fairhaven_tax.validate.checks import validate_cross_source_pin_alignment
        prc = _prc(50, pin_prefix="1314_99_")
        sales = _sales(50, pin_prefix="1314_10_")  # disjoint
        modiv = _modiv(50, pin_prefix="1314_99_")
        assert validate_cross_source_pin_alignment(prc, sales, modiv).passed is False

    def test_no_negative_assessments_pass(self):
        from fairhaven_tax.validate.checks import validate_no_negative_assessments
        assert validate_no_negative_assessments(_prc(100)).passed is True

    def test_no_negative_assessments_fail(self):
        from fairhaven_tax.validate.checks import validate_no_negative_assessments
        assert validate_no_negative_assessments(_prc(100, negative_assessment=True)).passed is False

    def test_run_phase2_gates_writes_report_with_source_column(self, tmp_path):
        from fairhaven_tax.validate.checks import run_phase2_gates
        prc = _prc(2060)
        sales = _sales(150)
        modiv = _modiv(50, year=2020)
        ok, results = run_phase2_gates(prc, sales, modiv, processed_dir=tmp_path)
        assert ok is True
        report_path = tmp_path / "validation_report.parquet"
        assert report_path.exists()
        report = pq.read_table(report_path).to_pandas()
        assert "source" in report.columns
        assert "phase2" in set(report["source"].tolist())

    def test_run_phase2_gates_appends_to_phase1_rows(self, tmp_path):
        """When a Phase-1 validation_report.parquet already exists, Phase 2 should
        tag those rows source='phase1' and append its own rows tagged 'phase2'."""
        from fairhaven_tax.validate.checks import run_phase2_gates
        # Seed a Phase-1 report (no source column).
        existing = pd.DataFrame([{
            "gate_name": "parcel_count",
            "expected": "2064",
            "actual": "2064",
            "tolerance": "0.05",
            "passed": True,
            "message": "phase 1 stub",
        }])
        pq.write_table(pa.Table.from_pandas(existing, preserve_index=False),
                       tmp_path / "validation_report.parquet")

        prc = _prc(2060)
        sales = _sales(150)
        modiv = _modiv(50, year=2020)
        run_phase2_gates(prc, sales, modiv, processed_dir=tmp_path)

        report = pq.read_table(tmp_path / "validation_report.parquet").to_pandas()
        sources = set(report["source"].tolist())
        assert "phase1" in sources
        assert "phase2" in sources

    def test_run_validation_script_exits_2_when_inputs_missing(self, tmp_path):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "run_validation.py"
        rc = subprocess.call(
            [sys.executable, str(script)],
            cwd=tmp_path,
            env={"PATH": os.environ.get("PATH", ""),
                 "PYTHONPATH": str(repo_root / "src")},
        )
        assert rc == 2, f"missing-inputs exit code expected 2, got {rc}"

    def test_run_validation_script_exits_1_on_gate_failure(self, tmp_path):
        """Synthetic prc parquet missing 50% of livable_area -> non-zero exit + fail doc."""
        proc_dir = tmp_path / "data" / "processed"
        proc_dir.mkdir(parents=True)

        # prc with 50% nulls in livable_area -> fails validate_prc_required_features
        bad_prc = _prc(2060, null_share=0.5)
        pq.write_table(pa.Table.from_pandas(bad_prc, preserve_index=False),
                       proc_dir / "prc.parquet")

        # Other inputs valid enough to proceed
        pq.write_table(pa.Table.from_pandas(_sales(200), preserve_index=False),
                       proc_dir / "sales.parquet")
        pq.write_table(pa.Table.from_pandas(_modiv(100, year=2020), preserve_index=False),
                       proc_dir / "modiv_history.parquet")
        # Minimal parcels parquet (Phase 1 may try to read it; we only require existence).
        import geopandas as gpd
        from shapely.geometry import Point
        gdf = gpd.GeoDataFrame(
            pd.DataFrame({"pams_pin": ["1314_10_0"], "assessed_value": [Decimal("500000")]}),
            geometry=[Point(0, 0)], crs="EPSG:3424",
        )
        gdf.to_parquet(proc_dir / "parcels.parquet")

        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "run_validation.py"
        rc = subprocess.call(
            [sys.executable, str(script)],
            cwd=tmp_path,
            env={"PATH": os.environ.get("PATH", ""),
                 "PYTHONPATH": str(repo_root / "src")},
        )
        assert rc == 1, f"gate-failure exit code expected 1, got {rc}"
        fail_doc = proc_dir / "_VALIDATION-FAILED.md"
        assert fail_doc.exists()


# ---------------------------------------------------------------------------
# Task 3 — Data-quality Astro viz
# ---------------------------------------------------------------------------


class TestDataQualityViz:
    def test_emits_chart_and_overlay_with_vega_lite_schema(self, tmp_path, monkeypatch):
        proc_dir = tmp_path / "data" / "processed"
        proc_dir.mkdir(parents=True)
        viz_dir = tmp_path / "viz" / "src" / "data"
        (viz_dir / "charts").mkdir(parents=True)
        (viz_dir / "overlays").mkdir(parents=True)

        # Synthetic 3-parcel prc, 2-row validation report.
        prc = _prc(3, null_share=0.0)
        # Inject one missing-feature parcel for tag coverage.
        prc.loc[0, "livable_area"] = None
        pq.write_table(pa.Table.from_pandas(prc, preserve_index=False),
                       proc_dir / "prc.parquet")

        report = pd.DataFrame([
            {"gate_name": "parcel_count", "expected": "2064", "actual": "2060",
             "tolerance": "0.05", "passed": True, "message": "ok", "source": "phase1"},
            {"gate_name": "prc_row_count", "expected": "2060", "actual": "3",
             "tolerance": "0.05", "passed": False, "message": "synthetic", "source": "phase2"},
        ])
        pq.write_table(pa.Table.from_pandas(report, preserve_index=False),
                       proc_dir / "validation_report.parquet")

        # Run the script with cwd=tmp_path so its hard-coded relative paths resolve.
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "build_data_quality_viz.py"
        rc = subprocess.call(
            [sys.executable, str(script)],
            cwd=tmp_path,
            env={"PATH": os.environ.get("PATH", ""),
                 "PYTHONPATH": str(repo_root / "src")},
        )
        assert rc == 0, f"script must exit 0, got {rc}"

        chart_path = viz_dir / "charts" / "data_quality.vl.json"
        overlay_path = viz_dir / "overlays" / "data_quality.json"
        assert chart_path.exists()
        assert overlay_path.exists()

        chart = json.loads(chart_path.read_text())
        assert chart["$schema"].startswith("https://vega.github.io/schema/vega-lite/")

        overlay = json.loads(overlay_path.read_text())
        assert isinstance(overlay, dict)
        assert "1314_10_0" in overlay
        assert "missing_livable_area" in overlay["1314_10_0"]

    def test_exits_2_on_missing_inputs(self, tmp_path):
        repo_root = Path(__file__).resolve().parent.parent
        script = repo_root / "scripts" / "build_data_quality_viz.py"
        rc = subprocess.call(
            [sys.executable, str(script)],
            cwd=tmp_path,
            env={"PATH": os.environ.get("PATH", ""),
                 "PYTHONPATH": str(repo_root / "src")},
        )
        assert rc == 2
