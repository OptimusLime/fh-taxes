# Roadmap: Fair Haven Tax Assessment Analysis

**Created:** 2026-04-28
**Granularity:** coarse (3 phases)
**Coverage:** 21/21 v1 requirements mapped
**MVP Decision Gate:** After Phase 3 ships, evaluate Berry shift magnitude + CDF gap test result to decide v2 go/no-go.

## Core Value

A reproducible, defensible parcel-level dollar-delta artifact (Berry tax-shift + CDF gap test) that either demonstrates tenure-correlated horizontal inequity in Fair Haven assessments, or documents that ADP works as designed. Either outcome is publishable.

## Phases

- [ ] **Phase 1: Data Foundation** - Acquire and persist three green-tier datasets (NJGIN parcels/MOD-IV, DLGS rate tables, DOT SR1A sales) with validated parcel universe and reconciled sales
- [ ] **Phase 2: Statistical Pipeline** - Hedonic OLS + Berry tax-shift + IAAO CDF gap test producing per-parcel delta_dollars and TRUE/FALSE chasing verdict
- [ ] **Phase 3: Public Artifact and Legal Compliance** - GeoJSON + Leaflet map + white paper shipped under Daniel's Law Redactor registration

## Phase Details

### Phase 1: Data Foundation
**Goal**: A queryable, validated parcel universe and sales table for Fair Haven (district 14) sourced exclusively from green-tier statewide datasets, ready to feed the hedonic.
**Depends on**: Nothing (entry phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, STORE-01, STORE-02
**Success Criteria** (what must be TRUE):
  1. Investigator can query the parcel universe by PAMS_PIN and the count is ~2,200 ±5% with aggregate assessed value ~$2.77B ±5%
  2. The 2025/2026 general tax rate ($1.574/$100), six-component breakdown, and total municipal levy are extracted from DLGS tables and stored as constants the pipeline can reference
  3. SR1A sales for 2018-2025 are filtered to Fair Haven arms-length transactions (NU codes 0/7/10/26/33) and reconciled against MOD-IV last-sale fields, with rejection reasons documented for excluded sales
  4. The parcel and sales tables persist in a queryable form (parquet/SQLite) and survive process restart without re-download
**Plans**: 2 plans
- [ ] 01-01-PLAN.md — Project skeleton + raw acquisition (uv project, package layout, three acquire scripts, manifest helper, per-year SR1A YAML mappers)
- [ ] 01-02-PLAN.md — Ingest, validate, persist, reconcile (NJGIN parcels GeoParquet, DLGS constants extraction, SR1A parser + rejections, last-sale resolution + MOD-IV reconciliation, ±5% validation gate)

### Phase 2: Statistical Pipeline
**Goal**: A reproducible Python pipeline that produces per-parcel `delta_dollars`, IAAO ratio-study diagnostics by tenure cohort, and a TRUE/FALSE CDF gap test verdict on Fair Haven sales 2018-2025.
**Depends on**: Phase 1
**Requirements**: MODEL-01, MODEL-02, MODEL-03, CALC-01, CALC-02, CALC-03, TEST-01
**Success Criteria** (what must be TRUE):
  1. Hedonic OLS fit on 2023-2025 arms-length sales reports R² ≥ 0.7 with HC3 robust SEs and k-means neighborhood fixed effects (k ∈ {5..8})
  2. Estimated true value applied to all ~2,200 class-2 parcels aggregates within 5% of $2.83B published total (constant correction documented if applied)
  3. Per-parcel Berry tax-shift `delta_dollars = actual_bill − fair_bill` is computed and Σ delta ≈ 0 within rounding tolerance
  4. Each parcel carries a `tenure_cohort` label, and cohort-level COD/PRD plus over/underpaying tail summaries are tabulated against IAAO standards (COD ≤15%, PRD 0.98-1.03)
  5. Python reimplementation of `assessr::detect_chasing()` runs end-to-end and emits a TRUE/FALSE result plus a CDF plot artifact
**Plans**: TBD

### Phase 3: Public Artifact and Legal Compliance
**Goal**: A publication-ready parcel-level GeoJSON + interactive Leaflet map + methodology white paper, shipped under valid Daniel's Law Redactor registration with owner names suppressed and reproducibility intact.
**Depends on**: Phase 2
**Requirements**: OUT-01, OUT-02, OUT-03, OUT-04, OUT-05, LEGAL-01, LEGAL-02, LEGAL-03
**Success Criteria** (what must be TRUE):
  1. Parcel-level GeoJSON exports with all eight required fields (assessed_value, estimated_true_value, fair_bill, actual_bill, delta_dollars, tenure_cohort, last_sale_date, last_sale_price) plus geometry, and contains zero owner-name fields
  2. A static Leaflet HTML page renders the GeoJSON with a diverging color scale centered at zero on `delta_dollars`, a tenure-cohort filter UI, per-parcel popups, and the CDF gap test result stamped at the top
  3. Static figures (CDF of assessment-to-sale ratio, ratio-vs-last-sale-year scatter with LOESS, cohort tax-bill stacked bars, residual choropleth) and the methodology white paper (every transformation, source URL, NU filter, model spec, verification check, limitation) are written as committed artifacts
  4. A single `make` target or shell script reproduces the full pipeline end-to-end from raw downloads, and a Jupyter/Quarto notebook contains the runnable code path
  5. OIP Daniel's Law Redactor registration is confirmed before publication; the public artifact cross-references the protected list and suppresses (or aggregates to BG) any matched parcels; framing language sticks to verifiable facts only with no imputation of motive
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Foundation | 0/2 | Not started | - |
| 2. Statistical Pipeline | 0/? | Not started | - |
| 3. Public Artifact and Legal Compliance | 0/? | Not started | - |

## Dependencies

```
Phase 1 (Data Foundation)
        |
        v
Phase 2 (Statistical Pipeline)
        |
        v
Phase 3 (Public Artifact + Legal Compliance) ---> MVP DECISION GATE
```

## MVP Decision Gate (after Phase 3)

Per PROJECT.md, evaluate v2 go/no-go using:
- **v2 justified**: Berry shift > ~$200K cohort-correlated AND CDF gap test TRUE
- **Diagnostic v2**: Mixed signal
- **Pivot artifact**: Both null → reframe as "ADP works as intended in Fair Haven" methodology demo

v2 requirements (DEMO-*, REG-*, BOE-*, EXT-*, PUB-*) are out of scope for this roadmap.

## Coverage Validation

All 21 v1 requirements map to exactly one phase:

- **Phase 1** (6): DATA-01, DATA-02, DATA-03, DATA-04, STORE-01, STORE-02
- **Phase 2** (7): MODEL-01, MODEL-02, MODEL-03, CALC-01, CALC-02, CALC-03, TEST-01
- **Phase 3** (8): OUT-01, OUT-02, OUT-03, OUT-04, OUT-05, LEGAL-01, LEGAL-02, LEGAL-03

No orphans. No duplicates.

> Note: REQUIREMENTS.md footer reported "23 total" but actual enumerated REQ-IDs total 21. Traceability table corrected to reflect actual count.

---
*Last updated: 2026-04-28 (roadmap creation)*
