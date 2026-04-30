# Requirements: Fair Haven Tax Assessment Analysis

**Defined:** 2026-04-29
**Core Value:** A reproducible, defensible parcel-level dollar-delta artifact (Berry tax-shift + CDF gap test) that either demonstrates tenure-correlated horizontal inequity in Fair Haven assessments, or documents that ADP works as designed.

## v1 Requirements

MVP scope: three green-tier downloads, one Python pipeline, one HTML output. Tests H1 (burden distribution) and H2 (passive sales chasing). H3 (BOE funding) is deferred to v2.

### Data Acquisition

- [x] **DATA-01** [CORRECTED 2026-04-29]: Acquire NJGIN Monmouth Parcels + MOD-IV file geodatabase from `https://geoapps.nj.gov/njgin/parcel/parcels_gdb_Monmouth.zip`. The FGDB has TWO layers (`parcels` for geometry, `tax_list` for MOD-IV attributes) joined on PAMS_PIN ↔ GIS_PIN. Filter MUN/CD_CODE = "1314" + PROP_CLASS = "2". Real measured values (2026-04-29 snapshot): 2,061 joined class-2 parcels, aggregate assessed = $2,735,202,500. Validates to ~2,064 ±5% / ~$2.74B ±5%.
- [x] **DATA-02** [CORRECTED 2026-04-29]: Acquire NJ DLGS Property Tax Tables from `https://www.nj.gov/dca/dlgs/resources/Property_Tax/{YY}_data/{YY}taxes.xls` (legacy `.xls`, not `.xlsx`). Fair Haven row in "Municipal Tax Summary" sheet has MuniCode = "1313" (DLGS scheme; differs from NJGIN's "1314"). Real 2025 values: total levy = $40,339,309.77; Net Valuation Taxable = $2,827,194,216; computed general rate = **$1.427 per $100** (PROJECT.md's $1.574 figure does not match published DLGS data and has been superseded). Levy breakdown captured into `constants.LEVY_BREAKDOWN` (14 keys including county/library/health/open-space/local-school/regional-school/municipal).
- [x] **DATA-03** [CORRECTED 2026-04-29]: Acquire NJ DOT SR1A annual sales files from `https://www.nj.gov/treasury/taxation/lpt/statdata/Sales{YYYY}.zip`. **Coverage = 2020-2025 (six years)**, not 2018-2025: 2018 and 2019 are not publicly available on NJ Treasury statdata page. SR1A is **fixed-width 663-byte records** (`.txt`), not CSV; layout per `https://www.nj.gov/treasury/taxation/pdf/lpt/SR1Afilelayout.pdf`. Filter county="13" + district="14". Arms-length per NJ DOT/IAAO convention = **NU code field BLANK** (or "0"/"00") — codes 01-33 enumerate Non-Usable categories. Original spec inverted this. Real measured: 197 arms-length sales, 705 rejections.
- [x] **DATA-04**: Cross-validate SR1A sales against MOD-IV per-parcel last-sale fields; reconcile discrepancies (>180 days OR >5% price diff) into `data/processed/reconciliation_diffs.parquet`. Real measured: 53 diffs flagged across 2,061 parcels. Non-blocking per D-19.

### OPRS Comprehensive Collection (Phase 1.5)

Added 2026-04-29 after real-data verification revealed MOD-IV does not carry bedrooms/bathrooms/condition (the original Phase 2 hedonic spec assumed it did). OPRS PRC PDFs publish those fields; Bloustein gives 37-year per-parcel history including `sale_assessment` (year-of-sale assessment).

- [ ] **DATA-05**: Cache `m4.cgi&hist=1` HTML for every class-2 Fair Haven parcel (~2,061). Each response content-validated for the requested block AND lot integers. Cache layout: `data/raw/oprs_prc/<pams_pin>/m4.html`.
- [ ] **DATA-06**: For every sale ssi enumerated from each parcel's m4, cache the corresponding `sr.cgi?ssi=N` HTML at `data/raw/oprs_prc/<pams_pin>/sr_<ssi>.html`. Empty-template responses (legitimate "no detail on record") get a `.no_sale` marker file rather than the empty HTML.
- [x] **DATA-07**: Cache the official PDF Property Record Card (`prc.cgi` → temp PDF) at `data/raw/oprs_prc/<pams_pin>/prc.pdf`. Apply the HTTP-header strip workaround (slice from `%PDF` marker) — upstream Apache returns PDF bytes with `Content-Type: text/html`. PDF must parse via pdfplumber and contain bedroom/bathroom/condition/story breakdown fields.
- [x] **DATA-08**: Cache the Chapter 75 statutory annual assessment notice PDF (`ch75.cgi` → temp PDF) at `data/raw/oprs_prc/<pams_pin>/ch75.pdf` and the current-year tax-list page PDF (`taxlist.cgi` → temp PDF) at `data/raw/oprs_prc/<pams_pin>/taxlist_<year>.pdf`. Both are valid PDF v1.4 (no header strip needed).
- [x] **DATA-09**: Cache Rutgers Bloustein MOD-IV historical CSV for Fair Haven for years 1989-2025 at `data/raw/bloustein_modiv/<date>/mod_iv_<year>.csv`. Each file ≥ 2,000 rows (Fair Haven typical 2,121-2,211 rows/year). Loader produces `data/processed/modiv_history.parquet` with one row per (parcel_pin, year). Include the per-year `sale_assessment` field (assessor's value at time of sale) — gold-standard input for the IAAO CDF gap test.

Out-of-scope OPRS endpoints (tax appeals, deed images, tax map sheets, subdivision maps, rate certifications, consolidated search) are documented in `.planning/deferred/oprs-tier-c.md` and are NOT promoted to v1 absent specific MVP-result-driven justification.

### Storage & Schema

- [x] **STORE-01**: Persist parcel universe in queryable form keyed by PAMS_PIN (parquet/SQLite acceptable for v1; PostGIS optional)
- [x] **STORE-02**: Persist sales table with parcel_pin, sale_date, sale_price, nu_code, deed_ref, source (SR1A vs MOD-IV)

### Statistical Pipeline

- [ ] **MODEL-01**: Generate neighborhood fixed-effect labels via k-means (k=5-8) on parcel centroids
- [ ] **MODEL-02** [REVISED 2026-04-29 against real MOD-IV schema]: Fit hedonic OLS on Fair Haven 2020-2025 arms-length sales (~197 sales total; ~92 in 2023-2025). **Available real features:** `log(sqft)` (from SR1A `LIVING-SPACE`, populated only on sale; or from MOD-IV `BLDG_DESC` text-extraction if needed), `log(lot_size_acres)` (MOD-IV `CALC_ACRE`), `year_built` (MOD-IV `YR_CONSTR`), `dwellings` (MOD-IV `DWELL`), property classification (`bldg_class`, `prop_use`), `neighborhood_FE` (k-means k=5-8). **NOT available:** `bedrooms`, `bathrooms`, `waterfront_flag` — these fields do not exist in MOD-IV's standard distribution. Original spec must be revised. statsmodels HC3 robust SEs; report R² (target ≥ 0.7).
- [ ] **MODEL-03** [CORRECTED 2026-04-29]: Apply hedonic to all 2,061 class-2 residential parcels with geometry; produce per-parcel `estimated_true_value`; aggregate within 5% of real measured $2.74B (was $2.83B from PROJECT.md narrative; real DLGS-published Net Valuation Taxable across ALL classes is $2.83B but class-2-only is $2.74B). Apply constant correction if needed.
- [ ] **CALC-01**: Compute Berry tax-shift per parcel — `fair_bill_i = (true_value_i / Σ true_value) × total_levy`; `actual_bill_i = assessed_value_i × tax_rate`; `delta_i = actual_bill_i − fair_bill_i`; verify Σ delta ≈ 0 within rounding
- [ ] **CALC-02**: Tag each parcel with `tenure_cohort` ∈ {pre-2010, 2010-2015, 2016-2019, 2020-2022, 2023-2026} from last arms-length sale date
- [ ] **CALC-03**: Tabulate cohort summaries — sum of positive deltas, sum of negative deltas, median delta, mean delta, share in over/underpaying tail per cohort; report COD and PRD overall and by cohort against IAAO standards (COD ≤15% acceptable, PRD 0.98-1.03 acceptable)
- [ ] **TEST-01** [CORRECTED 2026-04-29]: Reimplement IAAO/CCAO `assessr::detect_chasing()` in Python (CDF gap method + distribution comparison method); run on Fair Haven sales 2020-2025 (197 arms-length); emit TRUE/FALSE result and CDF plot. Note: ratio = sale-price / assessed-value-at-time-of-sale. SR1A `main_assessed_total` field captures the assessment in effect at sale; use that as denominator.

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
| DATA-01 | Phase 1 | Complete |
| DATA-02 | Phase 1 | Complete |
| DATA-03 | Phase 1 | Complete |
| DATA-04 | Phase 1 | Complete |
| STORE-01 | Phase 1 | Complete |
| STORE-02 | Phase 1 | Complete |
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
