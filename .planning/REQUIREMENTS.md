# Requirements: Fair Haven Tax Assessment Analysis

**Defined:** 2026-04-29
**Core Value:** A reproducible, defensible parcel-level dollar-delta artifact (Berry tax-shift + CDF gap test) that either demonstrates tenure-correlated horizontal inequity in Fair Haven assessments, or documents that ADP works as designed.

## v1 Requirements

MVP scope: three green-tier downloads, one Python pipeline, one HTML output. Tests H1 (burden distribution) and H2 (passive sales chasing). H3 (BOE funding) is deferred to v2.

### Data Acquisition

- [ ] **DATA-01**: Acquire NJGIN Monmouth Parcels + MOD-IV file geodatabase; filter to MUN_CODE = 1314 (Fair Haven); parcel count validates to ~2,200 ±5%; total assessed value validates to ~$2.77B ±5%
- [ ] **DATA-02**: Acquire NJ DLGS Property Tax Tables; extract Fair Haven 2025/2026 general tax rate ($1.574/$100), six-component breakdown (muni/county/library/local-school/regional-school/open-space), and total municipal levy
- [ ] **DATA-03**: Acquire NJ DOT SR1A annual sales files for 2018-2025; filter to Fair Haven (district 14) arms-length sales (NU codes ∈ {0, 7, 10, 26, 33})
- [ ] **DATA-04**: Cross-validate SR1A sales against MOD-IV per-parcel last-sale fields; reconcile discrepancies; document rejection reasons for excluded sales

### Storage & Schema

- [ ] **STORE-01**: Persist parcel universe in queryable form keyed by PAMS_PIN (parquet/SQLite acceptable for v1; PostGIS optional)
- [ ] **STORE-02**: Persist sales table with parcel_pin, sale_date, sale_price, nu_code, deed_ref, source (SR1A vs MOD-IV)

### Statistical Pipeline

- [ ] **MODEL-01**: Generate neighborhood fixed-effect labels via k-means (k=5-8) on parcel centroids
- [ ] **MODEL-02**: Fit hedonic OLS `log(sale_price) ~ log(sqft) + log(lot_size) + year_built + bedrooms + bathrooms + waterfront_flag + neighborhood_FE` on Fair Haven 2023-2025 arms-length sales; statsmodels with HC3 robust SEs; report R² (target ≥ 0.7)
- [ ] **MODEL-03**: Apply hedonic to all ~2,200 class-2 residential parcels; produce per-parcel `estimated_true_value`; aggregate within 5% of $2.83B published total (apply constant correction if needed)
- [ ] **CALC-01**: Compute Berry tax-shift per parcel — `fair_bill_i = (true_value_i / Σ true_value) × total_levy`; `actual_bill_i = assessed_value_i × tax_rate`; `delta_i = actual_bill_i − fair_bill_i`; verify Σ delta ≈ 0 within rounding
- [ ] **CALC-02**: Tag each parcel with `tenure_cohort` ∈ {pre-2010, 2010-2015, 2016-2019, 2020-2022, 2023-2026} from last arms-length sale date
- [ ] **CALC-03**: Tabulate cohort summaries — sum of positive deltas, sum of negative deltas, median delta, mean delta, share in over/underpaying tail per cohort; report COD and PRD overall and by cohort against IAAO standards (COD ≤15% acceptable, PRD 0.98-1.03 acceptable)
- [ ] **TEST-01**: Reimplement IAAO/CCAO `assessr::detect_chasing()` in Python (CDF gap method + distribution comparison method); run on Fair Haven sales 2018-2025; emit TRUE/FALSE result and CDF plot

### Output Artifacts

- [ ] **OUT-01**: Export parcel-level GeoJSON containing per-parcel `assessed_value`, `estimated_true_value`, `fair_bill`, `actual_bill`, `delta_dollars`, `tenure_cohort`, `last_sale_date`, `last_sale_price`, geometry
- [ ] **OUT-02**: Build static Leaflet HTML page rendering the GeoJSON with diverging color scale on `delta_dollars` (centered at zero), tenure cohort filter UI, per-parcel popup, and CDF gap test result stamped at top
- [ ] **OUT-03**: Generate static figures — CDF of assessment-to-sale ratio, scatter of ratio vs last-sale year with LOESS overlay, cohort tax-bill distribution stacked bars, residual choropleth
- [ ] **OUT-04**: Methodology white paper (Markdown/PDF) documenting every transformation, source URL, NU code filter, model spec, parameters, verification check, and known limitations
- [ ] **OUT-05**: Reproducibility — Jupyter or Quarto notebook with all code, plus a `make` or shell script that runs the full pipeline end-to-end from raw downloads

### Legal & Publication Compliance

- [ ] **LEGAL-01**: Register with OIP Daniel's Law Portal (`danielslaw.nj.gov`) as a Redactor before any public publication
- [ ] **LEGAL-02**: Suppress owner names from all public artifacts; cross-reference Daniel's Law protected list and suppress matched parcels (or aggregate to BG level for those parcels)
- [ ] **LEGAL-03**: Public artifact framing — verifiable facts only, no imputation of motive; methodology disclosure to support fair-comment / anti-SLAPP defense

## v2 Requirements

Conditional on MVP signal (Berry shift > ~$200K cohort-correlated AND/OR CDF gap test TRUE).

### Demographic Overlay

- **DEMO-01**: Census Geocoder API to map parcel addresses → block group
- **DEMO-02**: Pull ACS 5-year tables (B25007, B25026, B11005, B19013, B25077, B25103) at BG level; spatial join to parcels
- **DEMO-03**: Spearman correlation tax-bill decile vs school-age-children share; vs householder age
- **DEMO-04**: Acquire Monmouth County voter file via Superintendent of Elections (N.J.S.A. 19:31-18.1); parcel-grain age/tenure overlay

### Inferential Layer

- **REG-01**: OLS `delta_i ~ cohort + property_chars + neighborhood_FE` with HC3 robust SEs, BG-clustered; cohort coefficients with interpretation
- **REG-02**: Robustness — drop top/bottom 1% on each char; cohort × year_built interactions; class-2-only restriction; instrument cohort with permit density
- **REG-03**: Spatial-lag hedonic via PySAL (KNN or DistanceBand W) if v1 Moran's I on residuals is significant
- **REG-04**: Rumson Borough placebo replication — same pipeline, same regional HS, same ADP cycle

### BOE Funding Analysis (H3)

- **BOE-01**: Build 15-year levy-by-purpose time series from DLGS Property Tax Tables (2010-2025) in nominal and CPI-adjusted dollars
- **BOE-02**: Pull NJ DOE Fall Enrollment workbooks 2014-2025; per-pupil spending Z-scores vs Rumson, Little Silver, Shrewsbury, Red Bank Regional from TGES
- **BOE-03**: Extract RFH Regional apportionment formula from regional UFB; decompose Fair Haven vs Rumson share over time
- **BOE-04**: Triangulate against published 2025 levy split (62.9% to schools)

### Extended Data Acquisition

- **EXT-01**: Playwright OPRS scraper (sticky-session ASP.NET, VIEWSTATE replay, 1-2 req/s) for multi-sale histories and PRC details
- **EXT-02**: OPRS tax appeal judgments scrape (iId=481) — successful appellant cohort
- **EXT-03**: Redfin stingray endpoint validation of estimated_true_value vs held-out 2024-2026 sales
- **EXT-04**: NJ DCA Construction Reporter aggregate permit volumes for instrument variable

### Public Dashboard v2

- **PUB-01**: Interactive web dashboard (replaces static Leaflet) with full filtering, time-slider over assessment years, methodology tab
- **PUB-02**: Aggregate / BG-level default views; parcel-level on opt-in toggle with explicit Daniel's Law disclaimer

## Out of Scope

| Feature | Reason |
|---------|--------|
| MOREMLS / FlexMLS access | License-gated; not legally accessible without REALTOR® licensure |
| NJ MVC vehicle/license data | DPPA-protected (18 U.S.C. § 2721); $2,500 floor + fees per violation |
| Parcel-level Fair Haven building permits | OPRA to Rumson shared construction office; high tipoff to investigator |
| Internal Fair Haven assessor correspondence / AFR-A applications | OPRA to Fair Haven Clerk; highest tipoff risk |
| Internal BOE budget worksheets beyond UFB | OPRA to BOE BA; high tipoff in small district |
| Zillow scraping at scale | Heavy anti-bot stack and ToS prohibition; Redfin is the v2 substitute |
| OPRA filed under own name with Fair Haven Borough | Operate in green/yellow tiers exclusively until ready to be public |
| Speaking at BOE/Council meetings before analysis is mature | Public minutes reveal investigator |
| Real-time data refresh | Annual reassessment cycle means annual refresh is sufficient |
| Owner-name display in public artifact | Daniel's Law $1,000/violation exposure; not necessary for the analytical claim |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| DATA-03 | Phase 1 | Pending |
| DATA-04 | Phase 1 | Pending |
| STORE-01 | Phase 1 | Pending |
| STORE-02 | Phase 1 | Pending |
| MODEL-01 | Phase 2 | Pending |
| MODEL-02 | Phase 2 | Pending |
| MODEL-03 | Phase 2 | Pending |
| CALC-01 | Phase 2 | Pending |
| CALC-02 | Phase 2 | Pending |
| CALC-03 | Phase 2 | Pending |
| TEST-01 | Phase 2 | Pending |
| OUT-01 | Phase 3 | Pending |
| OUT-02 | Phase 3 | Pending |
| OUT-03 | Phase 3 | Pending |
| OUT-04 | Phase 3 | Pending |
| OUT-05 | Phase 3 | Pending |
| LEGAL-01 | Phase 3 | Pending |
| LEGAL-02 | Phase 3 | Pending |
| LEGAL-03 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 21 total (corrected from earlier "23 total" — actual enumerated REQ-IDs total 21)
- Mapped to phases: 21
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-29*
*Last updated: 2026-04-28 after roadmap creation (traceability populated)*
