---
phase: 01-data-foundation
plan: 01
subsystem: data-foundation
tags: [bootstrap, ingest, manifest, sr1a, njgin, dlgs, uv, parquet]
requires: []
provides:
  - "uv-managed Python project skeleton (D-02/D-03)"
  - "src/fairhaven_tax/ package importable"
  - "constants module with MUN_CODE, NU code arms-length filter, CRS, validation tolerances"
  - "manifest write/verify helpers (sha256, atomic, ISO-8601 UTC)"
  - "three CLI acquire scripts (NJGIN / DLGS / SR1A) with FAIRHAVEN_*_URL env-var override"
  - "8 per-year SR1A column-mapper YAMLs (2018-2025) per D-16"
  - "Makefile pipeline orchestration entrypoint"
affects:
  - "Plan 2 will consume manifest helpers, constants, SR1A column maps"
tech-stack:
  added:
    - "uv 0.9.27 — project + dependency management (D-02)"
    - "geopandas 1.1.3, pyarrow 24.0.0 — Parquet/GeoParquet storage (D-01)"
    - "typer 0.25.0 — CLI framework"
    - "structlog 25.5.0 — logging"
    - "pdfplumber 0.11.9, openpyxl 3.1.5, xlrd 2.0.2 — DLGS parsing (xls/xlsx drift)"
    - "pytest 9.0.3, ruff 0.15.12 — dev tooling"
  patterns:
    - "manifest.json (URL + sha256 + retrieved_at) is the reproducibility lever, not git-lfs (D-08)"
    - "Atomic write via .tmp + .replace() for manifest.json"
    - "Streaming download with 1 MiB chunks; .part suffix during transfer"
    - "Env-var URL override per source (FAIRHAVEN_NJGIN_URL, FAIRHAVEN_DLGS_URL, FAIRHAVEN_SR1A_URL_<YYYY>) to absorb URL rotation without code change"
    - "Per-year YAML column mappers for SR1A — tolerant of NJ Treasury schema drift"
key-files:
  created:
    - "pyproject.toml"
    - "uv.lock"
    - ".python-version"
    - ".gitignore"
    - "Makefile"
    - "README.md"
    - "src/fairhaven_tax/__init__.py"
    - "src/fairhaven_tax/constants.py"
    - "src/fairhaven_tax/cli.py"
    - "src/fairhaven_tax/ingest/__init__.py"
    - "src/fairhaven_tax/ingest/manifest.py"
    - "src/fairhaven_tax/ingest/njgin.py"
    - "src/fairhaven_tax/ingest/dlgs.py"
    - "src/fairhaven_tax/ingest/sr1a/__init__.py"
    - "src/fairhaven_tax/ingest/sr1a/columns/{2018..2025}.yaml"
    - "src/fairhaven_tax/validate/__init__.py"
    - "src/fairhaven_tax/persist/__init__.py"
    - "scripts/acquire_njgin.py"
    - "scripts/acquire_dlgs.py"
    - "scripts/acquire_sr1a.py"
    - "tests/__init__.py"
    - "tests/test_constants.py"
    - "tests/test_manifest.py"
    - "docs/manifests/manifest_schema.md"
  modified: []
decisions:
  - "Used `uv sync` (not `uv init`) and wrote pyproject.toml directly to control package layout per D-03"
  - "Pinned both `openpyxl` and `xlrd` as DLGS file format has drifted between .xls and .xlsx historically"
  - "Acquire scripts return distinct exit codes (0=ok, 1=partial, 2=total failure) so downstream Make targets can distinguish hard failure from partial-year coverage"
  - "Stored SR1A `archive_for_year()` filename as `sr1a-{YYYY}.zip` matching the URL pattern; if NJ Treasury switches archive structure, override via FAIRHAVEN_SR1A_URL_{YYYY}"
  - "Did NOT run `make acquire` against live network — see Network Limitations section"
metrics:
  duration: "~3.5 min"
  tasks_completed: "2/2"
  tests_added: 7
  tests_passed: 7
  files_created: 25
completed: "2026-04-29T12:27:12Z"
---

# Phase 1 Plan 1: Data Foundation Bootstrap Summary

uv-managed Python project skeleton with `src/fairhaven_tax/` layout, three CLI acquisition scripts (NJGIN / DLGS / SR1A) writing dated raw snapshots with sha256-verified manifest.json, and 8 per-year SR1A column-mapper YAMLs ready for Plan 2 ingestion.

## What Was Built

**Project skeleton (Task 1):**
- `pyproject.toml` declaring 17 runtime deps + 3 dev deps under `requires-python = ">=3.11,<3.13"`
- `src/fairhaven_tax/` package with `ingest/`, `validate/`, `persist/` subpackages and an `ingest/sr1a/` sub-subpackage
- `constants.py` exposing `MUN_CODE_FAIR_HAVEN="1314"`, `SR1A_ARMS_LENGTH_NU_CODES=frozenset({"0","07","10","26","33"})`, `CRS_NATIVE="EPSG:3424"`, `CRS_EXPORT="EPSG:4326"`, `VALIDATION_TOLERANCE=Decimal("0.05")` and stubs for the Plan-2-populated `TAX_RATE_PER_HUNDRED` / `TOTAL_LEVY` / `LEVY_BREAKDOWN`
- `cli.py` typer entrypoint stub
- `Makefile` with `install`, `acquire`, `acquire-njgin`, `acquire-dlgs`, `acquire-sr1a`, `ingest`, `validate`, `all`, `test`, `clean` targets
- `.gitignore` excluding `data/raw/`, `data/processed/`, `.venv/`, caches

**Acquisition layer (Task 2):**
- `ingest/manifest.py` exporting 6 names: `ManifestEntry` (frozen slotted dataclass), `sha256_file()`, `utcnow_iso()`, `snapshot_dir()`, `write_manifest()` (atomic), `verify_manifest()` (sha256 + bytes), `download_with_manifest_entry()` (streaming requests with project User-Agent)
- `ingest/njgin.py`, `ingest/dlgs.py`: source URL + archive filename constants
- `ingest/sr1a/__init__.py`: `COVERAGE_YEARS = list(range(2018, 2026))`, `url_for_year()`, `archive_for_year()`
- 8 SR1A YAML mappers (2018.yaml..2025.yaml) with canonical schema mapping, type coercions (`string_zfill_2` for nu_code/district), and PAMS_PIN derivation pattern
- 3 acquire scripts (`acquire_njgin.py`, `acquire_dlgs.py`, `acquire_sr1a.py`) with env-var URL override hooks
- `tests/test_manifest.py`: roundtrip, corruption-detection, snapshot_dir tests
- `docs/manifests/manifest_schema.md`: D-06 schema documentation

## Acceptance Criteria Status

All criteria from both tasks pass:

- `uv sync` succeeded (uv.lock created, .venv populated, 52 packages resolved)
- `uv run python -c "import fairhaven_tax"` exit 0
- `uv run pytest -q` → 7 passed (4 constants + 3 manifest)
- `make help` prints all 11 targets including `acquire`
- `find . -name "*.ipynb" -o -name "*.qmd"` (excluding .venv) → 0 results
- `grep -E "(sqlalchemy|psycopg|sqlite3|postgis)" pyproject.toml` → empty
- `data/raw/` and `data/processed/` are in `.gitignore`
- 8 YAML files (2018..2025) in `src/fairhaven_tax/ingest/sr1a/columns/`, all parse via `yaml.safe_load`, all contain `nu_code` mapping
- All 6 manifest exports importable
- All 3 acquire scripts pass `ast.parse()`
- `docs/manifests/manifest_schema.md` documents `sha256` and `retrieved_at`

## Final Resolved Dep Set (project .venv)

| Package | Version |
|---|---|
| geopandas | 1.1.3 |
| pyarrow | 24.0.0 |
| pandas | 3.0.2 |
| numpy | 2.4.4 |
| shapely | 2.1.2 |
| pyproj | (resolved transitively) |
| fiona | 1.10.1 |
| statsmodels | 0.14.6 |
| scikit-learn | 1.8.0 |
| scipy | 1.17.1 |
| requests | 2.33.1 |
| pyyaml | (resolved transitively) |
| typer | 0.25.0 |
| pdfplumber | 0.11.9 |
| openpyxl | 3.1.5 |
| xlrd | 2.0.2 |
| structlog | 25.5.0 |
| pytest | 9.0.3 |
| pytest-cov | 7.1.0 |
| ruff | 0.15.12 |

(`uv pip list` against the project venv reports 52 packages including transitives. Lockfile `uv.lock` is committed and pins the full graph.)

## Network Limitations

Per the executor brief: outbound network was not exercised. The acquire scripts were NOT invoked against the live NJGIN / DLGS / NJ Treasury endpoints. Validation was confined to:

- Syntax/import validation (`ast.parse` + import-test)
- Manifest helpers tested end-to-end against an in-tmp_path fake "downloaded" file (sha256 roundtrip + corruption-detection)
- Script `--help` not implemented (scripts are positional-arg-free; they print progress lines and call `download_with_manifest_entry`)

**Live URL verification deferred to a manual `make acquire` run by the user, or to Plan 2 prerequisites.** If any URL has rotated since the canonical references in `01-CONTEXT.md`, the operator can override per-source via:

- `FAIRHAVEN_NJGIN_URL` (NJGIN ArcGIS Hub item GUID may shift)
- `FAIRHAVEN_DLGS_URL` (DLGS file format has drifted .xls ↔ .xlsx historically; current default is `25taxes.xlsx`)
- `FAIRHAVEN_SR1A_URL_<YYYY>` (per-year override; current pattern `sr1a-{YYYY}.zip`)

The default URLs are the best canonical references documented in `01-CONTEXT.md` as of the planning date; record any rotated URLs in Plan 2's SUMMARY.

## Deviations from Plan

None. Plan executed exactly as written. No bugs found, no missing critical functionality, no blocking issues, no architectural changes.

## Self-Check: PASSED

Verified:
- `pyproject.toml` exists at repo root
- `src/fairhaven_tax/__init__.py` exists; `__version__ == "0.1.0"`
- `src/fairhaven_tax/ingest/manifest.py` exists; all 6 exports importable
- 8 YAML files present at `src/fairhaven_tax/ingest/sr1a/columns/{2018..2025}.yaml`
- 3 acquire scripts present at `scripts/acquire_{njgin,dlgs,sr1a}.py`
- 7 pytest tests pass
- Commit `d8c7c7a` (Task 1) found in `git log`
- Commit `c565876` (Task 2) found in `git log`
