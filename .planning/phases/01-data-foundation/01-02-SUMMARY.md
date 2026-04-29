---
phase: 01-data-foundation
plan: 02
subsystem: data-foundation
tags: [ingest, validate, reconcile, parquet, geoparquet, sr1a, mod-iv, dlgs, hard-fail]
requires:
  - "01-01: uv project skeleton, constants.py stubs, manifest helpers, 8 SR1A YAML mappers, acquire scripts"
provides:
  - "data/processed/parcels.parquet (GeoParquet, EPSG:3424) — class-2 Fair Haven parcels with denormalized last-sale columns"
  - "data/processed/sales.parquet — arms-length SR1A sales 2018-2025 keyed by parcel_pin"
  - "data/processed/rejections.parquet — audit trail of every SR1A row filtered out, with controlled-vocab rejection_reason"
  - "data/processed/reconciliation_diffs.parquet — MOD-IV ↔ SR1A last-sale discrepancies (>180d OR >5% price)"
  - "data/processed/validation_report.parquet — per-gate pass/fail with expected/actual"
  - "data/processed/_VALIDATION-FAILED.md (only on out-of-tolerance) + exit non-zero (D-09)"
  - "src/fairhaven_tax/validate/gates.py — three gates per D-11; run_all_gates aggregates"
  - "src/fairhaven_tax/validate/reconcile.py — resolve_last_arms_length_sale (D-18), reconcile_last_sale (D-19)"
  - "src/fairhaven_tax/ingest/sr1a/parse.py — per-year YAML-driven parser"
  - "src/fairhaven_tax/ingest/pams_pin.py — canonical PAMS_PIN constructor"
  - "src/fairhaven_tax/persist/parquet_io.py — read/write helpers"
  - "scripts/{ingest_njgin,extract_dlgs,ingest_sr1a,reconcile,validate_phase1}.py drivers"
  - "fairhaven-tax CLI subcommands: version, ingest, validate"
affects:
  - "Phase 2 hedonic + Berry tax-shift consume parcels.parquet (with denormalized last-sale columns) and sales.parquet (training set)"
  - "Phase 2 imports constants.py for TAX_RATE_PER_HUNDRED, TOTAL_LEVY, LEVY_BREAKDOWN (populated by extract_dlgs.py at runtime)"
  - "Phase 3 GeoJSON export reprojects parcels.parquet from EPSG:3424 → EPSG:4326 (D-14)"
tech-stack:
  added:
    - "pyyaml — driver for per-year SR1A column mappers (D-16)"
    - "shapely.geometry — used in test fixtures only"
  patterns:
    - "YAML-driven schema mapping for SR1A absorbs NJ Treasury format drift without code change (D-16)"
    - "Controlled-vocabulary rejection_reason on every dropped SR1A row (D-12 audit trail)"
    - "Hard-fail validation with markdown failure-doc artifact + non-zero exit code (D-09)"
    - "Decimal preservation: all monetary values stay as Decimal in pandas object columns; no float coercion"
    - "MAX(date) tie-break MAX(price) via single sort_values + drop_duplicates (D-18)"
    - "MOD-IV/SR1A reconciliation is descriptive-only (writes diffs, does not block) (D-19)"
    - "GeoParquet refuses to write CRS-less frames (defensive)"
key-files:
  created:
    - "docs/schemas/parcels.md"
    - "docs/schemas/sales.md"
    - "docs/schemas/rejections.md"
    - "src/fairhaven_tax/ingest/pams_pin.py"
    - "src/fairhaven_tax/ingest/sr1a/parse.py"
    - "src/fairhaven_tax/persist/parquet_io.py"
    - "src/fairhaven_tax/validate/gates.py"
    - "src/fairhaven_tax/validate/reconcile.py"
    - "scripts/ingest_njgin.py"
    - "scripts/extract_dlgs.py"
    - "scripts/ingest_sr1a.py"
    - "scripts/reconcile.py"
    - "scripts/validate_phase1.py"
    - "tests/test_pams_pin.py"
    - "tests/test_sr1a_parse.py"
    - "tests/test_reconcile.py"
    - "tests/test_validate_gates.py"
  modified:
    - "src/fairhaven_tax/cli.py — added ingest and validate subcommands"
    - "Makefile — added ingest-njgin / extract-dlgs / ingest-sr1a / reconcile targets; replaced ingest recipe"
decisions:
  - "Implemented hard-fail at full strength (D-09): _VALIDATION-FAILED.md artifact + sys.exit(1). No 'warn' downgrade."
  - "NU code '0'/'00' both normalize to '0' (matches canonical SR1A_ARMS_LENGTH_NU_CODES set without forcing the set to include both)"
  - "SR1A parser handles CSV/TXT-in-zip; DBF support deferred with explicit NotImplementedError (keeps surface tight; only added if a year actually ships DBF)"
  - "Reconciliation is non-blocking (D-19) — diffs.parquet written even when empty; validation gate does NOT consume diffs"
  - "Live data acquisition NOT exercised in this environment (network constraint per executor brief). Coverage is unit-test driven on synthetic fixtures, including a full hard-fail integration test that runs scripts/validate_phase1.py as a subprocess."
  - "Used `Decimal | None` typing throughout; `pyarrow.decimal128` postponed (object-dtype Decimals round-trip cleanly through write_parquet)"
metrics:
  duration: "~7.3 min"
  tasks_completed: "2/2"
  tests_added: 25
  tests_passed: 32
  files_created: 17
  files_modified: 2
completed: "2026-04-29T12:37:45Z"
---

# Phase 1 Plan 2: Data Foundation Ingest+Validate Summary

YAML-driven SR1A parser, MOD-IV/SR1A last-sale reconciliation per D-18/D-19, and a hard-fail validation gate (D-09) wrapping the three validation targets in `data/processed/validation_report.parquet`.

## What Was Built

**Schemas + helpers (Task 1):**
- `docs/schemas/{parcels,sales,rejections}.md` — canonical column sets; rejections vocabulary fixed at six values
- `ingest/pams_pin.py` — `build_pams_pin(district, block, lot, qualifier)` with district zfill(2), `"nan"`/`"None"` qualifier coalescing, plus inverse `parse_pams_pin`
- `persist/parquet_io.py` — `write_parquet`, `write_geoparquet` (refuses CRS-less), `read_parquet`, `read_geoparquet`, `ensure_processed_dir`
- `scripts/ingest_njgin.py` — FGDB → parcels.parquet with column-alias resolver (canonical → multiple source aliases), CRS hard-fail per D-15, `MUN_CODE`/`PROPERTY_CLASS` filter using constants directly
- `scripts/extract_dlgs.py` — header-token scanner for the DLGS xlsx; rewrites constants.py via `re.MULTILINE` substitutions on three lines

**Parser + validation + reconcile (Task 2):**
- `ingest/sr1a/parse.py` — `parse_sr1a_year` and `parse_sr1a_all`; CSV/TXT-in-zip detection (multiple delimiter fallbacks); typed coercions per YAML; D-12 NU code normalization with the `"0"/"00"` special case; deterministic filter ordering (district → required → nu_code) routing failures to rejections
- `validate/gates.py` — three gates using constants directly (`VALIDATION_TOLERANCE`, `EXPECTED_PARCEL_COUNT`, `EXPECTED_AGGREGATE_ASSESSED`, `SR1A_MIN_ARMS_LENGTH_SALES_2018_2025`); writes `validation_report.parquet`; exposes `ValidationFailure`
- `validate/reconcile.py` — `resolve_last_arms_length_sale` (single sort_values+drop_duplicates per D-18); `reconcile_last_sale` (left-join, source labelling sr1a/modiv/null, diff thresholding at 180 days OR `VALIDATION_TOLERANCE`)
- `scripts/{ingest_sr1a,reconcile,validate_phase1}.py` drivers; `validate_phase1.py` writes `_VALIDATION-FAILED.md` and `sys.exit(1)` on failure
- CLI gains `ingest` (chains all four scripts via subprocess) and `validate` subcommands

## Acceptance Criteria Status

All Task 1 + Task 2 criteria pass:

- 32/32 tests pass (4 constants + 3 manifest + 7 pams_pin + 6 sr1a_parse + 5 reconcile + 7 validate_gates)
- All required exports importable: `validate.gates.{validate_parcel_count, validate_aggregate_assessed, validate_sales_floor, run_all_gates, ValidationFailure}`, `validate.reconcile.{reconcile_last_sale, resolve_last_arms_length_sale}`, `ingest.sr1a.parse.{parse_sr1a_year, parse_sr1a_all}`, `persist.parquet_io.{write_parquet, write_geoparquet, read_parquet, read_geoparquet, ensure_processed_dir}`
- `grep "_VALIDATION-FAILED.md" scripts/validate_phase1.py` → 3 hits
- `grep "sys.exit(1)" scripts/validate_phase1.py` → 1 hit
- `grep "SR1A_ARMS_LENGTH_NU_CODES" src/fairhaven_tax/ingest/sr1a/parse.py` → 1 hit (parser uses canonical set)
- `grep "MAX(sale_date)" src/fairhaven_tax/validate/reconcile.py` → 3 hits (D-18 visible)
- `grep "180" src/fairhaven_tax/validate/reconcile.py` → 3 hits; `grep "VALIDATION_TOLERANCE" .../reconcile.py` → 1 hit (D-19 thresholds present)
- `grep -E "VALIDATION_TOLERANCE|EXPECTED_PARCEL_COUNT|EXPECTED_AGGREGATE_ASSESSED" src/fairhaven_tax/validate/gates.py` → 4 hits (gates use constants)
- `uv run fairhaven-tax --help` lists `version`, `ingest`, `validate`
- `find . -name "*.ipynb" -o -name "*.qmd"` (excluding .venv) → 0 results
- `grep -rE "import sqlite3|from sqlalchemy|import psycopg" src/ scripts/` → empty
- `scripts/ingest_njgin.py` and `scripts/extract_dlgs.py` parse via `ast.parse()`

## Hard-Fail Behavior — Demonstrated

A dedicated test (`test_validate_phase1_hard_fails_writes_artifact`) builds a synthetic out-of-tolerance fixture (5,000 parcels vs expected 2,200), stages it as `data/processed/parcels.parquet` + `sales.parquet` in a tmp_path, runs `scripts/validate_phase1.py` as a subprocess, and asserts:

- subprocess exit code is non-zero
- `_VALIDATION-FAILED.md` is written to `data/processed/`
- the markdown contains the gate-result table with the failing `parcel_count` row

This satisfies the success criterion: "Hard-fail validation behavior demonstrated by a unit test (synthetic out-of-tolerance fixture → exit non-zero + `_VALIDATION-FAILED.md` written)".

## Network / Data Limitations

The executor brief and Plan 1 SUMMARY noted that outbound network and live raw data were not exercised. Consequently:

- `make ingest`, `make all`, `make extract-dlgs` are **not** invoked end-to-end in this environment.
- `data/processed/{parcels,sales,rejections,reconciliation_diffs,validation_report}.parquet` are not produced — they are produced when the user runs `make all` against a populated `data/raw/`.
- `constants.py` still has `TAX_RATE_PER_HUNDRED = None` etc.; `make extract-dlgs` will populate these on first live run. The rewriter logic is unit-trivial (regex + `Decimal()`) and the parser scans for headers on a tolerant pattern set (`COMPONENT_HEADER_PATTERNS`).
- DLGS column-header drift cannot be evaluated until the live xlsx is fetched. The script emits a clear hint pointing at `COMPONENT_HEADER_PATTERNS` if scan fails.
- Per-year SR1A schema drift cannot be evaluated until live archives arrive. Synthetic fixtures use the canonical 2025 column set; per-year YAML mappers live at `src/fairhaven_tax/ingest/sr1a/columns/{2018..2025}.yaml` and can be edited per year as drift surfaces.

**Live verification belongs to the user running `make all` after this plan ships.** The unit-test surface is robust:

| Layer | Coverage |
|---|---|
| PAMS_PIN construction | 7 tests (basic, district zfill, qualifier, block letters, roundtrip, parse error, "nan" coalesce) |
| SR1A parser | 6 tests (NU filter, district filter, unparseable date, district zfill, PAMS_PIN integration, "0"/"00" normalization) |
| Reconciliation | 5 tests (MAX-date, tie-break MAX-price, diff>180d, no-diff in tolerance, source assignment sr1a/modiv/null) |
| Validation gates | 7 tests (count pass/fail/boundary, aggregate within/outside, sales floor edge, report write, hard-fail integration) |

## Known Stubs

- `bedrooms` / `bathrooms` in `parcels.parquet` are emitted as `None` regardless of MOD-IV content. The MOD-IV FGDB does not expose those fields under the canonical aliases configured in `COLUMN_ALIASES`. Phase 2 will need to extend the alias set or accept that those features come from a different source. Documented for follow-up; non-blocking for Phase 1's validation gate.
- `waterfront_flag` is `False` for every parcel. Plan 2 explicitly defers this refinement to Phase 2 (`docs/schemas/parcels.md` notes "Default false in Phase 1; Phase 2 may refine").
- `last_sale_*` columns on `parcels.parquet` are written by `scripts/reconcile.py` (Task 2). The NJGIN ingest output (Task 1) seeds them with `None`; the reconcile pass populates them. This is intentional — not a stub.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or trust-boundary schema changes introduced beyond what Plan 1's threat model already covered (manifest verification, controlled raw-data root).

## Deviations from Plan

**Auto-fixed during implementation:**

**1. [Rule 1 — Bug] `test_parse_invalid` used a 4-part string**
- **Found during:** Task 1 verification (`uv run pytest tests/test_pams_pin.py`)
- **Issue:** Original spec used `"not_a_valid_pin"` as the "invalid PIN" fixture. That string contains exactly 4 underscore-separated parts, so `parse_pams_pin` accepts it without raising.
- **Fix:** Replaced with `"only_three_parts"` (3 underscore-separated parts) so the invariant is genuinely tested.
- **File:** `tests/test_pams_pin.py`
- **Commit:** `551176a` (Task 1)

**2. [Rule 1 — Bug] `test_reconcile_source_assignment` strict-`is None` check**
- **Found during:** Task 2 verification.
- **Issue:** Pandas coerces `None` in a string column to `NaN` after concat/merge, so `assert source is None` fails on the third row.
- **Fix:** Accept either `None` or `NaN` as "no source resolved".
- **File:** `tests/test_reconcile.py`
- **Commit:** `cb92d0d` (Task 2)

**3. [Rule 2 — Critical] Added a hard-fail integration test exercising scripts/validate_phase1.py end-to-end**
- **Found during:** Task 2 verification — plan listed only unit-level tests for the gates module, but the executor brief's success criteria explicitly required: *"Hard-fail validation behavior demonstrated by a unit test (synthetic out-of-tolerance fixture → exit non-zero + `_VALIDATION-FAILED.md` written)"*.
- **Fix:** Added `test_validate_phase1_hard_fails_writes_artifact` which constructs a 5,000-parcel synthetic fixture, stages it in a tmp_path, runs `scripts/validate_phase1.py` as a subprocess, and asserts the failure artifact + non-zero exit code.
- **File:** `tests/test_validate_gates.py`
- **Commit:** `cb92d0d` (Task 2)

No architectural changes (Rule 4) needed.

## Authentication Gates

None — no auth required for this plan.

## Self-Check: PASSED

Verified:
- `docs/schemas/{parcels,sales,rejections}.md` all exist
- `src/fairhaven_tax/ingest/pams_pin.py`, `src/fairhaven_tax/ingest/sr1a/parse.py`, `src/fairhaven_tax/persist/parquet_io.py`, `src/fairhaven_tax/validate/gates.py`, `src/fairhaven_tax/validate/reconcile.py` all exist and import cleanly
- `scripts/ingest_njgin.py`, `scripts/extract_dlgs.py`, `scripts/ingest_sr1a.py`, `scripts/reconcile.py`, `scripts/validate_phase1.py` all exist and `ast.parse()` clean
- `tests/test_pams_pin.py` (7), `tests/test_sr1a_parse.py` (6), `tests/test_reconcile.py` (5), `tests/test_validate_gates.py` (7) all run; total suite: 32/32 pass
- Commit `551176a` (Task 1) found in `git log`
- Commit `cb92d0d` (Task 2) found in `git log`
- `find . -name "*.ipynb" -o -name "*.qmd"` → 0 (notebooks remain categorically excluded)
- `grep -rE "import sqlite3|from sqlalchemy|import psycopg" src/ scripts/` → empty (no SQL backends)
- `uv run fairhaven-tax --help` lists `ingest`, `validate`, `version`
