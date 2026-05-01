---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: milestone
status: executing
stopped_at: Completed 02-04-PLAN.md
last_updated: "2026-05-01T00:18:32.077Z"
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 15
  completed_plans: 11
  percent: 73
---

# State: Fair Haven Tax Assessment Analysis

## Project Reference

**Core Value:** A reproducible, defensible parcel-level dollar-delta artifact (Berry tax-shift + CDF gap test) that either demonstrates tenure-correlated horizontal inequity in Fair Haven assessments, or documents that ADP works as designed.

**Current Focus:** Phase 02 — statistical-pipeline

## Current Position

Phase: 02 (statistical-pipeline) — EXECUTING
Plan: 4 of 7 (wave-2 complete; wave-3 next: Plans 5/6/7 parallel)

- **Milestone:** v1 MVP
- **Phase:** 01-data-foundation
- **Plan:** Phase 1 complete; ready to transition to Phase 2 (statistical core)
- **Status:** Executing Phase 02

**Progress:** [███████░░░] 73%

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases complete | 0/3 |
| Plans complete | 0/0 |
| Requirements validated | 0/21 |
| Sessions | 1 (initialization) |
| Phase 01-data-foundation P01 | 3.5min | 2 tasks | 25 files |
| Phase 01-data-foundation P02 | 7.3min | 2 tasks | 17 files |
| Phase 01.5 P01 | 25m | 2 tasks | 2 files |
| Phase 01.5 P06 | 25min | 2 tasks | 4 files |
| Phase 01.5 P04 | 22min | 2 tasks | 9 files |
| Phase 01.5 P05 | 12min | 1 tasks | 2 files |
| Phase 02 P01 | 25min | 3 tasks | 8 files |
| Phase 02 P04 | 50min | 2 tasks | 9 files |

## Accumulated Context

### Key Decisions (carried forward from PROJECT.md)

- Coarse granularity → 3-phase MVP shape (data → stats → artifact+legal)
- Three green-tier datasets only for v1 (NJGIN, DLGS, SR1A); no OPRA to Fair Haven until post-MVP
- Class 2 residential only in v1 (commercial/exempt distort hedonic)
- Owner names fully suppressed in public artifact (Daniel's Law $1,000/violation exposure)
- Pre-commitment to publish either direction (falsification of H1+H2+H3 is itself publishable)
- H2 framed as passive sales chasing, not stale assessments (ADP makes stale-assessment hypothesis structurally weak)

### Phase 1 Decisions (Plan 01-01)

- Used uv + pyproject.toml directly (not `uv init` defaults) to control `src/fairhaven_tax/` layout per D-03
- Manifest helpers use atomic write + sha256 verification; reproducibility via manifest.json (not git-lfs per D-08)
- Acquire scripts support `FAIRHAVEN_*_URL` env-var override to absorb URL rotation without code change
- Pinned both openpyxl and xlrd; DLGS file format has drifted .xls ↔ .xlsx historically
- DATA-01, DATA-02, DATA-03 acquisition leg satisfied (live download deferred to user / Plan 2 prerequisite)

### Phase 1 Decisions (Plan 01-02)

- Hard-fail validation gate writes `_VALIDATION-FAILED.md` and exits non-zero (D-09) — no warn downgrade
- NU code "0" and "00" both normalize to "0" — preserves canonical SR1A_ARMS_LENGTH_NU_CODES set
- MOD-IV/SR1A reconciliation is non-blocking (D-19) — `reconciliation_diffs.parquet` always written, never affects validation gate
- SR1A parser handles CSV/TXT-in-zip; DBF deferred behind explicit NotImplementedError (only added when a year ships DBF)
- Live data acquisition NOT exercised in this environment; coverage is unit-test driven on synthetic fixtures (32/32 tests pass), including a hard-fail integration test that runs `scripts/validate_phase1.py` as a subprocess
- DATA-01..04 + STORE-01..02 satisfied (live `make all` end-to-end deferred to user)

### Phase 2 Decisions (Plan 02-01)

- Phase-2 validation gate operational; live run flags `condition` column at 84% non-null (real data-quality issue for Plan 04 hedonic spec to address — drop, impute, or revise feature set)
- `atomic_write_json` is the single canonical .tmp+rename helper for all `viz/src/data/**` writes (D-63 hot-reload)
- IAAO/CDF/hedonic constants centralised in `constants.py`; Phase-2 gates source thresholds from there
- HISTORICAL_TAX_RATES wired up with 2025 verified + fallback; 2020-2024 deferred (cache only has 2025)

### Phase 2 Decisions (Plan 02-04 — hedonic OLS)

- Achieved R²=0.7155, adj R²=0.6778 on n=155 sales (197 → arms-length → 2020-2025 → feature-complete); MODEL-02 0.70 target met
- k-means neighborhood FE swept over {5,6,7,8} by silhouette → k=7 chosen (silhouette 0.381 vs k=6's 0.380)
- Used `effective_build_year = notice_year − eff_age` (with year_built fallback) instead of raw year_built — captures the assessor's renovation-aware build-year estimate (Phase 1.5 follow-up)
- `lot_size_clipped` = acreage clipped at 0.01 acre — keeps log() defined for the 922 condo/zero-acreage class-2 parcels
- `livable_area<=0` → NaN before imputation (8 parcels affected)
- Calibration factor 0.8878 applied (pre-cal sum was 12.6% above target; post-cal Σ matches \$2.74B exactly per MODEL-03)
- Duan's smearing factor 1.0288 applied to all exponentiated predictions
- Phase-2 gate `prc_required_features` failure on `condition` is downgraded to a warning in `run_hedonic.py` (hedonic imputes within-neighborhood medians; all other gate failures remain blocking)
- MODEL-01, MODEL-02, MODEL-03 all satisfied

### Open Todos

- Run `make all` against live network (user) to populate `data/processed/` and verify URLs are still canonical
- Phase 2: Berry tax-shift calculation (Plan 5; CALC-01/02), IAAO ratio study (Plan 6), CDF gap test (Plan 7; TEST-01)

### Blockers

None.

### Methodology Anchors

- IAAO Standard on Ratio Studies (April 2013) — COD/PRD thresholds
- Indiana 50 IAC 27-2-11 — sales-chasing CDF gap test specification
- Cook County Assessor `assessr` R package — reference implementation to port to Python
- Christopher Berry / U Chicago CMF — Berry tax-shift methodology
- Pace, Barry, Clapp & Rodriguez (1998); Can (1992) — spatial-lag hedonics (deferred to v2)

### MVP Decision Gate (post-Phase 3)

- Berry shift > ~$200K cohort-correlated AND CDF gap test TRUE → v2 justified
- Mixed signal → diagnostic v2
- Both null → pivot artifact framing to "ADP works as intended" methodology demo

## Session Continuity

**Last session:** 2026-05-01T00:18:16.396Z
**Stopped at:** Completed 02-04-PLAN.md
**Next session:** Transition Phase 1 → 2 — `/gsd-transition`

### Resume Instructions

1. Read `.planning/phases/01-data-foundation/01-02-SUMMARY.md` for phase completion state
2. Read `.planning/REQUIREMENTS.md` for remaining v1 scope (PIPE/MODEL/CALC/TEST/OUT/LEGAL/DOC)
3. Run `/gsd-transition` to advance to Phase 2 (statistical core: hedonic + Berry tax-shift)

---
*Last updated: 2026-04-28 (roadmap creation)*
