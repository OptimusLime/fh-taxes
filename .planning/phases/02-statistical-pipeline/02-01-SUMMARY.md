---
phase: 02-statistical-pipeline
plan: 01
subsystem: validate, persist, viz
tags: [validation-gate, wave-0-prep, altair, atomic-json, iaao-thresholds]
requires:
  - data/processed/prc.parquet (D-32, Phase 1.5 build_prc_parquet)
  - data/processed/sales.parquet (Phase 1 ingest_sr1a)
  - data/processed/parcels.parquet (Phase 1 ingest_njgin)
  - data/processed/modiv_history.parquet (D-34, Phase 1.5 build_modiv_history)
provides:
  - src/fairhaven_tax/validate/checks.py::run_phase2_gates
  - src/fairhaven_tax/persist/json_io.py::atomic_write_json
  - constants.RANDOM_SEED, IAAO_*, HEDONIC_*, CDF_*, HISTORICAL_TAX_RATES{,_FALLBACK}
  - scripts/run_validation.py (POSIX 0/1/2 exit codes)
  - scripts/build_data_quality_viz.py
  - viz/src/data/charts/data_quality.vl.json
  - viz/src/data/overlays/data_quality.json
  - viz/public/leaflet/ landing dir
affects:
  - data/processed/validation_report.parquet (extended with `source` column)
tech-stack:
  added:
    - altair==6.1.0 (resolved from >=5.5,<7)
  patterns:
    - atomic .tmp + Path.replace JSON writes (D-63)
    - source-tagged combined Phase-1+Phase-2 validation report
key-files:
  created:
    - src/fairhaven_tax/persist/json_io.py
    - src/fairhaven_tax/validate/checks.py
    - scripts/run_validation.py
    - scripts/build_data_quality_viz.py
    - tests/test_validate_checks.py
    - viz/public/leaflet/.gitkeep
    - viz/src/data/charts/data_quality.vl.json
    - viz/src/data/overlays/data_quality.json
  modified:
    - pyproject.toml (added altair)
    - uv.lock (resolved altair==6.1.0 + transitive deps)
    - src/fairhaven_tax/constants.py (Phase-2 constants block)
    - src/fairhaven_tax/validate/__init__.py (re-exports)
decisions:
  - "Phase-2 gates target real prc schema (current_year_assessment, acreage); plan's draft column names (current_assessed_total, lot_size_acres) corrected against the live D-32 schema."
  - "Cross-source PIN alignment uses set intersection across the three source PIN columns (pams_pin in prc, parcel_pin in sales/modiv) — all use the same 1314_block_lot[_qual] scheme."
  - "Live data run exits 1: condition column is 84% non-null in real prc.parquet (below the 95% threshold). This is a real data-quality finding for Plan 04 hedonic spec, NOT a bug in the gate."
  - "Historical tax rate extraction (issue #3a): only 2025 cached; 2020-2024 left to fallback per plan's best-effort spec. Documented as known limitation."
metrics:
  duration: 25min
  completed: 2026-04-29
---

# Phase 2 Plan 01: Validation Gate + Wave-0 Prep Summary

**One-liner:** Phase-2 validation gate (7 new gates over prc/sales/modiv_history) plus Wave-0 prep (altair, RANDOM_SEED + IAAO/CDF/hedonic constants, atomic JSON helper, Leaflet landing dir, data-quality Astro viz).

## Tasks Completed

| Task | Commit | Files |
|------|--------|-------|
| 1. Wave-0 prep | b98c4fa | pyproject.toml, uv.lock, constants.py, json_io.py, viz/public/leaflet/.gitkeep, tests/test_validate_checks.py |
| 2. Phase-2 gates + CLI | 6370330 | validate/checks.py, validate/__init__.py, scripts/run_validation.py, tests/test_validate_checks.py |
| 3. Data-quality viz | 0a3a3fa | scripts/build_data_quality_viz.py, viz/src/data/charts/data_quality.vl.json, viz/src/data/overlays/data_quality.json |

## Gates Added (7 Phase-2 + 3 Phase-1 = 10 total)

| Gate | Checks | Threshold |
|------|--------|-----------|
| `validate_prc_required_features` | min non-null share across 7 hedonic feature cols | ≥0.95 |
| `validate_prc_row_count` | total prc rows | 2060 ±5% |
| `validate_sales_row_count` | SR1A arms-length sales count | ≥`SR1A_MIN_ARMS_LENGTH_SALES` (100) |
| `validate_sales_year_range` | every derivable sale_year ∈ [2020, 2025] | 0 out-of-range |
| `validate_modiv_history_sale_assessment` | rows with sale_price+sale_assessment in [2014,2025] | ≥`CDF_TEST_MIN_N` (30) |
| `validate_cross_source_pin_alignment` | sales PINs present in BOTH prc AND modiv | ≥0.95 alignment rate |
| `validate_no_negative_assessments` | `current_year_assessment` < 0 count | =0 |

`run_phase2_gates` aggregates these and extends `validation_report.parquet` with a `source` column ('phase1' | 'phase2'). Existing Phase-1 rows are tagged 'phase1' on append.

## Constants Added to `src/fairhaven_tax/constants.py`

```python
RANDOM_SEED: int = 42
IAAO_COD_RESIDENTIAL_MAX: Decimal = Decimal("15.0")
IAAO_COD_RESIDENTIAL_MIN: Decimal = Decimal("5.0")
IAAO_PRD_MIN: Decimal = Decimal("0.98")
IAAO_PRD_MAX: Decimal = Decimal("1.03")
IAAO_PRB_MIN: Decimal = Decimal("-0.05")
IAAO_PRB_MAX: Decimal = Decimal("0.05")
HEDONIC_TRAIN_YEAR_MIN: int = 2020
HEDONIC_TRAIN_YEAR_MAX: int = 2025
HEDONIC_K_NEIGHBORHOOD_DEFAULT: int = 6
HEDONIC_R2_TARGET: Decimal = Decimal("0.7")
CDF_GAP_BOUNDS: tuple[Decimal, Decimal] = (Decimal("0.98"), Decimal("1.02"))
CDF_GAP_THRESHOLD: Decimal = Decimal("0.03")
CDF_TEST_YEAR_MIN: int = 2014
CDF_TEST_YEAR_MAX: int = 2025
CDF_TEST_MIN_N: int = 30
HISTORICAL_TAX_RATES: dict[int, Decimal] = { 2025: Decimal("1.427") }
HISTORICAL_TAX_RATES_FALLBACK: Decimal = Decimal("1.427")
```

## Schema Reconciliation (deviations from plan's draft column names)

The plan's task-2 prose mentioned `current_assessed_total` and `lot_size_acres`; the real D-32 prc.parquet uses **`current_year_assessment`** and **`acreage`**. Gates target the real schema; the negative-assessment gate has a defensive fallback to `current_assessed_total` if a future schema migration adds it. Documented in `validate/checks.py` module docstring.

The plan also assumed sales has `sale_year`; the real sales.parquet has `sale_date` only — `validate_sales_year_range` derives the year from `sale_date` if `sale_year` is absent.

## Live Data Findings

Running `uv run python scripts/run_validation.py` against the real `data/processed/`:

- **FAILS** on `prc_required_features`: column `condition` is 84% non-null (need ≥95%). This is a **real Phase-2 data-quality finding** — Plan 04 (hedonic) will need to either drop `condition`, impute it, or expand the feature set so that the worst-case missingness column is below threshold. The gate is doing exactly what it's designed to do: blocking downstream plans until upstream feature coverage is sufficient or the spec is revised.
- All other 6 gates PASS:
  - prc_row_count: 2060 rows (matches expected exactly)
  - sales_row_count: 197 (above floor 100)
  - sales_year_range: all 197 sales in 2020-2025
  - modiv_history_sale_assessment: 19,193 rows in [2014,2025] post-ADP
  - cross_source_pin_alignment: 96.91% (188/194 sales PINs in prc∩modiv)
  - no_negative_assessments: 0 negatives

## Historical Tax Rate Extraction (issue #3a, best-effort)

Plan called for extraction of 2020-2024 Fair Haven general tax rates from cached DLGS files. Cache currently contains only `2026-04-29/25taxes.xls` (2025 only). 2020-2024 require live HTTPS fetches from `https://www.nj.gov/dca/dlgs/resources/property_tax/{YYYY}/property_tax_tables.html`, deferred for this run.

Per plan: best-effort, success defined as "the dict and fallback both exist and are wired up." Both exist:

- `HISTORICAL_TAX_RATES = {2025: Decimal("1.427")}` (verified)
- `HISTORICAL_TAX_RATES_FALLBACK = Decimal("1.427")` (used by Plan 05 with `limitation_flag=True` for missing years)

`TestHistoricalRates.test_dict_well_formed_for_phase2_window` asserts the dict-or-fallback contract.

## Atomic JSON Contract (D-63)

`atomic_write_json` is the single canonical helper. Altair's `chart.save()` writes directly (non-atomic), so `build_data_quality_viz.py` re-routes its output: writes to a `.raw` sibling, parses the JSON, and re-emits via `atomic_write_json` to honour the `.tmp + Path.replace` contract.

## Data-Quality Viz Outputs (live run)

- `viz/src/data/charts/data_quality.vl.json` — 10-row Vega-Lite bar chart, schema = `https://vega.github.io/schema/vega-lite/v6.4.1.json`.
- `viz/src/data/overlays/data_quality.json` — dict keyed by `pams_pin` (2060 entries; 353 PINs carry one or more issue tags, predominantly `missing_condition`).

## Total Gate Count After Merge

10 gates in `data/processed/validation_report.parquet`:
- 3 phase1 (parcel_count, aggregate_assessed, sales_floor)
- 7 phase2 (listed above)

## Synthetic-Fixture Quirks for Downstream Plans

- `_prc()` in tests defaults to all parcels with PIN prefix `1314_10_<idx>`; if a downstream test wants disjoint PIN sets it must override `pin_prefix`.
- `_modiv()` defaults to `year=2020` (post-ADP) and both `sale_price` + `sale_assessment` filled — convenient for CDF gap-test fixtures (Plan 7).
- The cross-source alignment test requires `prc_n >= sales_n` AND `modiv_n >= sales_n` with overlapping prefixes; downstream plans' integration tests should mirror this (or expect alignment failure).

## Test Counts

29 tests in `tests/test_validate_checks.py` — all pass:
- TestPrep: 6
- TestHistoricalRates: 3
- TestPhase2Gates: 18 (incl. 2 subprocess tests on `run_validation.py`)
- TestDataQualityViz: 2 (subprocess tests on `build_data_quality_viz.py`)

## Deviations from Plan

### Auto-fixed Issues (Rule 1 — Bug)

**1. [Rule 1 — Bug] Plan's draft column names did not match real prc schema.**
- **Found during:** Task 2 verification (live data run).
- **Issue:** Plan referenced `current_assessed_total` and `lot_size_acres`; real prc.parquet uses `current_year_assessment` and `acreage`.
- **Fix:** Gates target the real schema; defensive fallback for `current_assessed_total` retained.
- **Files modified:** `src/fairhaven_tax/validate/checks.py`
- **Commit:** 6370330

**2. [Rule 1 — Bug] Sales lacks `sale_year` column.**
- **Found during:** Task 2 implementation.
- **Issue:** Plan's gate definition assumed a `sale_year` column; real sales.parquet only has `sale_date`.
- **Fix:** `validate_sales_year_range` derives year from `sale_date` when `sale_year` is absent.
- **Commit:** 6370330

### Auth Gates

None.

### Architectural / Decision Checkpoints

None — all deviations were schema reconciliations covered by Rule 1.

## Self-Check: PASSED

- `src/fairhaven_tax/persist/json_io.py` exists ✓
- `src/fairhaven_tax/validate/checks.py` exists ✓
- `scripts/run_validation.py` exists ✓
- `scripts/build_data_quality_viz.py` exists ✓
- `viz/public/leaflet/.gitkeep` exists ✓
- `viz/src/data/charts/data_quality.vl.json` exists ✓
- `viz/src/data/overlays/data_quality.json` exists ✓
- `tests/test_validate_checks.py` exists (29 tests) ✓
- Commits b98c4fa, 6370330, 0a3a3fa all in `git log` ✓
