# Roadmap: Fair Haven Tax Assessment Analysis

**Created:** 2026-04-28
**Last revised:** 2026-04-29 (inserted Phase 1.5 + Bloustein historical addition)
**Granularity:** coarse (4 phases including 1.5)
**Coverage:** 26/26 v1 requirements mapped (added DATA-05..09)
**MVP Decision Gate:** After Phase 3 ships, evaluate Berry shift magnitude + CDF gap test result to decide v2 go/no-go.

## Core Value

A reproducible, defensible parcel-level dollar-delta artifact (Berry tax-shift + CDF gap test) that either demonstrates tenure-correlated horizontal inequity in Fair Haven assessments, or documents that ADP works as designed. Either outcome is publishable.

## Phases

- [x] **Phase 1: Data Foundation** - Acquire and persist three green-tier datasets (NJGIN parcels/MOD-IV, DLGS rate tables, DOT SR1A sales) with validated parcel universe and reconciled sales
- [ ] **Phase 1.5: OPRS Comprehensive Collection** - Cache full OPRS Property Record Card data (m4 + per-sale sr + prc PDF + ch75 PDF + taxlist PDF) and Bloustein 1989-2025 historical for all class-2 parcels. Unlocks bedrooms/bathrooms/condition for the hedonic and 37-year per-parcel assessment time series for the CDF gap test.
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
- [x] 01-01-PLAN.md — Project skeleton + raw acquisition (uv project, package layout, three acquire scripts, manifest helper, per-year SR1A YAML mappers)
- [x] 01-02-PLAN.md — Ingest, validate, persist, reconcile (NJGIN parcels GeoParquet, DLGS constants extraction, SR1A parser + rejections, last-sale resolution + MOD-IV reconciliation, ±5% validation gate)

### Phase 1.5: OPRS Comprehensive Collection (+ Bloustein historical)
**Goal**: A complete per-parcel cache of Monmouth OPRS Property Record Card data — basic PRC summary, per-sale detail for every recorded sale, official PRC PDF (with bedrooms/bathrooms/condition/sketch), Chapter 75 annual notice PDF, and current-year tax-list PDF — for all 2,061 class-2 Fair Haven parcels. Plus the full Rutgers Bloustein MOD-IV historical CSV series 1989-2025 (per-parcel year-by-year assessment time series with sale_assessment per recorded sale). Unlocks the hedonic feature set the original spec assumed and provides a 37-year longitudinal record for the CDF gap test.
**Depends on**: Phase 1
**Requirements**: DATA-05, DATA-06, DATA-07, DATA-08, DATA-09
**Success Criteria** (what must be TRUE):
  1. `data/raw/oprs_prc/<pams_pin>/m4.html` cached for all 2,061 class-2 parcels with content-validated block/lot match
  2. `data/raw/oprs_prc/<pams_pin>/sr_<ssi>.html` cached for every sale ssi enumerated from each parcel's m4 (or `.no_sale` marker for ssis that legitimately return empty)
  3. `data/raw/oprs_prc/<pams_pin>/prc.pdf` cached with HTTP-header strip (response body slice from `%PDF` marker) — bedroom/bathroom/condition data extractable
  4. `data/raw/oprs_prc/<pams_pin>/ch75.pdf` and `data/raw/oprs_prc/<pams_pin>/taxlist_<year>.pdf` cached as valid PDF v1.4 documents
  5. `data/raw/bloustein_modiv/<date>/mod_iv_{1989..2025}.csv` cached with row counts ≥ 2,000 each (37 files, no partial downloads)
  6. Parser produces `data/processed/prc.parquet` joining all OPRS components by PAMS_PIN with bedrooms, bathrooms, room_count, kitchens, livable_area, condition, quality_grade, foundation, exterior, roof, heating, AC, sewer, fireplaces, garage_sqft, porch_sqft, eff_age — every field the Phase 2 hedonic needs
  7. Bloustein loader produces `data/processed/modiv_history.parquet` with one row per (parcel_pin, year) and includes `sale_assessment` for parcels that sold that year (the gold-standard input for the CDF gap test)
**Plans**: 6 plans
- [x] 01.5-01-PLAN.md — Extend collect_oprs.py with prc/ch75/taxlist PDF endpoints (D-27/D-28/D-30) [DATA-07, DATA-08]
- [x] 01.5-02-PLAN.md — Operator-driven comprehensive collection across 2,061 parcels with VPN-swap loop [DATA-05..08]
- [ ] 01.5-03-PLAN.md — OPRS HTML parsers: parse_m4.py + parse_sr.py with unit tests [DATA-05, DATA-06]
- [x] 01.5-04-PLAN.md — OPRS PDF parsers: parse_prc_pdf + parse_ch75_pdf + parse_taxlist_pdf via pdfplumber [DATA-07, DATA-08]
- [ ] 01.5-05-PLAN.md — scripts/build_prc_parquet.py aggregator → data/processed/prc.parquet + sales enrichment [DATA-05..08]
- [x] 01.5-06-PLAN.md — Bloustein loader (src/fairhaven_tax/ingest/bloustein.py) + scripts/build_modiv_history.py → modiv_history.parquet [DATA-09]
**Notes**: Tier-C OPRS endpoints (tax appeals, deed images, tax maps, etc.) are explicitly out of scope — see `.planning/deferred/oprs-tier-c.md`.

### Phase 2: Statistical Pipeline
**Goal**: A reproducible Python pipeline that produces per-parcel `delta_dollars`, IAAO ratio-study diagnostics by tenure cohort, and a TRUE/FALSE CDF gap test verdict on Fair Haven sales 2018-2025.
**Depends on**: Phase 1, Phase 1.5
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
| 1. Data Foundation | 2/2 | Complete | 2026-04-29 |
| 1.5. OPRS Comprehensive Collection | 0/? | In planning | - |
| 2. Statistical Pipeline | 0/? | Blocked on 1.5 | - |
| 3. Public Artifact and Legal Compliance | 0/? | Blocked on 2 | - |

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

All 26 v1 requirements map to exactly one phase:

- **Phase 1** (6): DATA-01, DATA-02, DATA-03, DATA-04, STORE-01, STORE-02
- **Phase 1.5** (5): DATA-05, DATA-06, DATA-07, DATA-08, DATA-09
- **Phase 2** (7): MODEL-01, MODEL-02, MODEL-03, CALC-01, CALC-02, CALC-03, TEST-01
- **Phase 3** (8): OUT-01, OUT-02, OUT-03, OUT-04, OUT-05, LEGAL-01, LEGAL-02, LEGAL-03

No orphans. No duplicates.

> Note: REQUIREMENTS.md footer reported "23 total" but actual enumerated REQ-IDs total 21. Traceability table corrected to reflect actual count.

---
*Last updated: 2026-04-28 (roadmap creation)*
