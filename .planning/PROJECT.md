# Fair Haven Tax Assessment Analysis

## What This Is

A data investigation and public-facing dashboard analyzing property tax burden distribution in Fair Haven Borough, NJ (Monmouth County, district 14). The project tests whether post-2020 movers bear a disproportionate share of the tax burden via passive sales chasing in Monmouth County's Assessment Demonstration Program (ADP), using the Berry tax-shift methodology (Cook County / U Chicago Center for Municipal Finance) and the IAAO sales-chasing CDF gap test. Output is a parcel-level dollar-delta GeoJSON rendered as an interactive Leaflet map, with methodology white paper.

## Core Value

A reproducible, defensible parcel-level dollar-delta artifact (Berry tax-shift + CDF gap test) that either (a) demonstrates tenure-correlated horizontal inequity in Fair Haven assessments, or (b) documents that ADP works as designed. Either outcome is publishable. Pre-commitment to publish either way is what distinguishes investigation from advocacy.

## Requirements

### Validated

(None yet — ship to validate)

### Active

**MVP (v1) — three downloads, one Python pipeline, one HTML output:**

- [ ] **DATA-01**: Acquire NJGIN Monmouth Parcels + MOD-IV file geodatabase; filter to MUN_CODE = 1314 (Fair Haven), keep class 2 residential
- [ ] **DATA-02**: Acquire NJ DLGS Property Tax Tables for current rate ($1.574/$100) and total levy
- [ ] **DATA-03**: Acquire NJ DOT SR1A annual sales files for 2018-2025; filter to Fair Haven arms-length sales (NU codes 0/7/10/26/33)
- [ ] **PIPE-01**: Build Python ingestion pipeline (geopandas) that loads MOD-IV, validates parcel count (~2,200) and total assessed value (~$2.77B) against published figures
- [ ] **MODEL-01**: Fit hedonic OLS: log(sale_price) ~ log(sqft) + log(lot_size) + year_built + bedrooms + bathrooms + waterfront_flag + neighborhood_FE (k-means k=5-8); statsmodels HC3 robust SEs; R² ≥ 0.7
- [ ] **MODEL-02**: Apply hedonic to all ~2,200 parcels; produce estimated_true_value; verify aggregate within 5% of $2.83B
- [ ] **CALC-01**: Compute Berry tax-shift per parcel: fair_bill, actual_bill, delta_dollars; verify Σ delta ≈ 0
- [ ] **CALC-02**: Tag each parcel with tenure_cohort (pre-2010, 2010-2015, 2016-2019, 2020-2022, 2023-2026)
- [ ] **TEST-01**: Reimplement assessr::detect_chasing() in Python; run on Fair Haven sales 2018-2025; produce CDF plot and TRUE/FALSE result
- [ ] **OUT-01**: Export parcel-level GeoJSON with all fields (assessed_value, estimated_true_value, fair_bill, actual_bill, delta_dollars, tenure_cohort, last_sale_date, last_sale_price)
- [ ] **OUT-02**: Build static Leaflet HTML with diverging color scale on delta_dollars, tenure cohort filter, per-parcel popup, CDF gap test result stamped at top
- [ ] **LEGAL-01**: Register with OIP Daniel's Law Portal as Redactor; suppress owner names; cross-reference protected list before publication
- [ ] **DOC-01**: Methodology white paper documenting every transformation, source, and assumption

### Out of Scope (v1, deferred to v2 conditional on signal)

- Census ACS demographic overlay (B25007, B25026, B11005, B19013) — v2 if MVP shows signal
- Monmouth County voter file age cross-reference — v2 only if BG-level ACS proves too coarse
- BOE longitudinal funding analysis (H3) — v2 unless DLGS time series alone resolves it directionally
- Comparative per-pupil spending vs Rumson/Little Silver/Shrewsbury — v2 (H3)
- Spatial-lag hedonic (PySAL inverse-distance W) — v2 only if v1 Moran's I on residuals is significant
- Monmouth OPRS scraping (Playwright VIEWSTATE replay) for multi-sale histories and PRC photos — v2
- Tax appeal cohort scraping (OPRS iId=481) — v2
- Redfin stingray endpoints for market-value validation — v2
- Rumson Borough placebo analysis — v2 robustness
- Regression inferential layer (cohort coefficient with HC3, BG-clustered SEs) — v2
- Demographic overlay correlations (Spearman tax decile vs school-age share) — v2

### Permanently Out of Scope

- MOREMLS / FlexMLS data — license-gated, not legally accessible
- NJ MVC vehicle/license data — DPPA-protected (18 U.S.C. § 2721)
- Parcel-level Fair Haven building permits — OPRA to Rumson shared construction office, high tipoff risk
- Internal Fair Haven assessor correspondence — OPRA to FH Clerk, highest tipoff risk
- Internal BOE budget worksheets beyond published UFB — OPRA to BOE BA, high tipoff
- Zillow scraping at scale — anti-bot stack + ToS prohibition; use Redfin in v2 if needed
- Speaking at BOE/Council meetings before analysis is mature — minutes are public, reveals investigator
- OPRA filed under own name with Fair Haven Borough — operate in green/yellow tiers exclusively until ready to be public

## Context

**Subject municipality:** Fair Haven Borough, Monmouth County, NJ. ~6,100 residents, ~2,200 households (~2,200 parcels), ~$2.83B aggregate true value, ~$2.77B assessed. 2025 Director's Ratio 101.96%. District code 14. General tax rate ~$1.574/$100 split: municipal $0.343, county $0.199, county library $0.014, local school $0.713, regional school (RFH) $0.277, county open space $0.028. Schools = ~63% of every bill. Annual reassessment under Monmouth ADP (P.L. 2013, c. 15; N.J.S.A. 54:1-101 et seq.) — 5-year rolling inspection cycle, January 15 appeal deadline, valuation date Oct 1 of pretax year. Assessor: Greg Hutchinson (RDS contractor for inspections).

**Investigator profile:** Resident, technical (Python/scraping/dashboards), publishing to public website, operating under-the-radar relative to town government.

**Central pivot (v2 of research plan):** H2 reframed from "stale assessments" (structurally weak in an ADP town) to **passive sales chasing** — a mass-appraisal artifact where recent sales serve as the strongest training signal, pinning sold parcels tightly to sale price while non-sold parcels drift. This is the statistical analogue of *West Milford v. Van Decker* (NJ 1990) and *Allegheny Pittsburgh Coal* (US 1989). ADP eliminates the legal version (overt spot reassessment); it does not immunize against the passive statistical version.

**Methodology anchors:** IAAO Standard on Ratio Studies (April 2013); Indiana 50 IAC 27-2-11; Cook County Assessor's Office `assessr` R package (open-source CDF gap test); Christopher Berry's Cook County tax-shift work ($1.7B / $2.2B headline figures, U Chicago CMF); Pace, Barry, Clapp & Rodriguez (1998) and Can (1992) for spatial-lag hedonics in v2.

**Hypotheses (research plan v2):**
- **H1 (primary)**: Burden distribution skews toward post-2020 buyers vs pre-2015 holders, even controlling for property characteristics
- **H2 (secondary, mechanism)**: Passive sales chasing produces tenure-correlated horizontal inequity invisible to the aggregate Director's Ratio
- **H3 (tertiary)**: Fair Haven BOE underfunded relative to revenue origin and peer K-8 districts (~$21,890 vs Rumson $26,317 per pupil)

**Decision gate after MVP:** (1) Berry shift > ~$200K across cohorts AND CDF gap test TRUE → v2 justified; (2) mixed → diagnostic v2; (3) both null → pivot artifact to "ADP works as intended in Fair Haven" methodology demo.

## Constraints

- **Tech stack**: Python (geopandas, statsmodels, scipy, scikit-learn for k-means, pdfplumber/camelot for DLGS PDFs). PostgreSQL + PostGIS keyed by PAMS_PIN if data volume warrants; SQLite/parquet acceptable for v1. Leaflet (static HTML) for the public map. PySAL deferred to v2.
- **Legal — Daniel's Law (N.J.S.A. 47:1B-1 et seq.)**: Must register as Redactor on OIP portal before publication; suppress matched parcels or redact owner names; mandatory $1,000-per-violation statutory damages. Default public visualizations to aggregate / BG level where individual identifiability is a concern; parcel-level map ships with owner names suppressed entirely.
- **Legal — defamation / anti-SLAPP**: Stick to verifiable facts (assessment, sale price, ratio, dollar delta). Avoid imputing motives. Frame as systemic critique not individual indictment. NJ UPEPA (N.J.S.A. 2A:53A-49 et seq.) provides anti-SLAPP cover for matters of public concern.
- **Legal — scraping**: Reasonable rate limits (1-2 req/s), identifying user-agent with contact email, respect robots.txt. Post-*hiQ v. LinkedIn* / *Van Buren* ToS violations are civil contract claims, not CFAA criminal.
- **Legal — voter file**: N.J.S.A. 19:31-18.1 — non-commercial use only, ≤$375/yr cap, request goes to Monmouth County Superintendent of Elections (invisible to FH Borough). DPPA does NOT cover voter rolls — joining MOD-IV with voter file is allowed.
- **Operational tipoff hierarchy**: Operate strictly in bottom four tiers (NJOGIS bulk → county voter → OPRS scraping → public meeting observer). No OPRA to Fair Haven Borough until analysis is mature. No MVC data ever (DPPA $2,500 floor + fees).
- **Pre-commitment**: Publish result regardless of direction. Falsification of H1+H2+H3 is itself a publishable finding.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| H2 framed as passive sales chasing (not stale assessments) | ADP makes stale-assessment hypothesis structurally weak; sales chasing is the right statistical mechanism in an annual-reassessment town and has Van Decker / Allegheny Pittsburgh anchor | — Pending |
| MVP uses 3 green-tier datasets only (NJGIN + DLGS + SR1A) | ~95% of analytical needs are invisible to FH Borough; OPRA filings reserved for after MVP signal confirms direction | — Pending |
| Coarse phase granularity | Project is research-investigation with clear MVP gate; over-decomposition would create churn before signal exists | — Pending |
| Skip parallel domain research | Provided research plan already covers stack, features, architecture, pitfalls in greater depth than agents would produce | — Pending |
| Quality model profile (Opus for research/roadmap) | Statistical methodology and legal analysis benefit from deeper reasoning; project scope is small (~2,200 parcels) so per-token cost is manageable | — Pending |
| Owner names suppressed in public artifact | Daniel's Law $1,000/violation exposure; Redactor registration is mandatory; parcel-level financials alone tell the story | — Pending |
| Class 2 residential only in v1 | Commercial (class 4) and exempt (class 15) parcels distort hedonic; can be added in v2 if needed | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-29 after initialization*
