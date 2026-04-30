# Phase 2: Statistical Pipeline — Research

**Researched:** 2026-04-29
**Domain:** Property tax horizontal-equity econometrics + Astro/Leaflet/Vega-Lite static viz
**Confidence:** HIGH on Berry methodology and assessr port (primary sources retrieved verbatim); HIGH on IAAO formulas (R source code retrieved verbatim); MEDIUM on Astro+Leaflet integration patterns (community packages exist but no single canonical pattern).

---

## TL;DR (read this first)

**Five locked recommendations for the planner:**

1. **Berry's "fair_bill" formula (D-55) — recommend Option (a) with explicit warning.** Berry's published Cook County methodology does **NOT** use a property-characteristics hedonic to compute fair_bill. He uses a **sales-only sample-and-extrapolate procedure**: fair_rate = Σ(actual_taxes_on_sold) / Σ(sale_prices_of_sold), then fair_bill_i = fair_rate × sale_price_i for sold homes only, then he stratifies and reweights to scale up to the population. **For Fair Haven we should run BOTH: (Berry-faithful) the sales-only fair-rate procedure on the 197 arms-length sales, AND (Option-a hedonic) the property-characteristics hedonic against `actual_bill` to produce per-parcel `delta_dollars` for ALL 2,061 parcels.** They answer different questions. The Berry-faithful version is the public anchor (D-50). The hedonic version is what produces a parcel-level map (the actual artifact).

2. **Hedonic spec — recommend `log(sale_price) ~ log(livable_area) + log(lot_size_acres) + year_built + bedrooms + bathrooms + condition + quality_grade + C(neighborhood_FE) + C(sale_year)` with HC3.** Berry's 2021 paper does NOT actually run this — his Eq. (1) is `ln(A/P) ~ α_jt + β·ln(P) + ε` (a regressivity-detection regression, not a value-prediction model). The hedonic spec we need is standard mass-appraisal practice (Gloudemans & Almy 2011) which Berry cites. Phase 1.5 unblocked bedrooms/bathrooms/condition via `prc.parquet` — use them.

3. **CDF gap test (D-66) — Python port is a 30-line direct translation.** Sort ratios, compute ECDF, find max diff between consecutive CDF values, return TRUE iff max_diff > 0.03 AND the location of that gap falls in (0.98, 1.02). Distribution test: compare actual %-in-bounds vs Monte Carlo normal-distribution %-in-bounds with same mean/sd. `detect_chasing()` returns TRUE only when BOTH methods return TRUE. Full pseudocode in Section 3.

4. **Astro + Leaflet + Vega-Lite stack — Astro 6 + leaflet 1.9 + vega-embed 7. Use `client:visible` (not `client:load`) for both map and charts.** Map is a `.astro` component that renders an empty `<div>` and a `<script>` block that dynamically imports leaflet on the client and reads `viz/src/data/parcels.geojson` via fetch. Charts use a thin Preact wrapper (`Chart.tsx`) that calls `vegaEmbed(el, spec)`.

5. **Effect-size threshold for "material" tax shift — use Berry's $800M-of-$2.235B = ~36% top-decile-share-of-total-shift as the calibration.** Translated to Fair Haven scale: total levy = $40.34M, sample-fraction-of-properties-sold per year ≈ 197/2061 = 9.6% (much higher than Cook's 2.5%), so a "material" finding would be a top-decile (or pre-2015 cohort) tax shift on the order of **$200K-$800K aggregate** per year. The decision-gate threshold from PROJECT.md ($200K cohort-correlated) is consistent.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-50** Replicate Cook County / Berry first-pass approach as north-star reference.
- **D-51** Statistical-power preference over tight-spec preference (197 sales 2020-2025 with year FE > 92 sales 2023-2025).
- **D-52** Yearly correctness within regime — no leaking 2024 sales into 2018 valuations.
- **D-53** Multi-tag tenure cohorts (orthogonal axes; `never_sold` and `family_sale_only` co-occur with tenure tags).
- **D-54** Hedonic training window: 2020-2025 (197 arms-length sales) with year FE.
- **D-55** CDF gap test scope: post-ADP (2014-2025) using Bloustein `sale_assessment` column.
- **D-57/D-58** Plans dependency-ordered, every plan ships viz; 8-plan locked outline.
- **D-59** Astro.js as the visualization framework (under `viz/`).
- **D-60** Map layer: Leaflet rendering parcel GeoJSON + per-parcel JSON overlays keyed by PAMS_PIN.
- **D-61** Chart layer: Altair → `*.vl.json` → Astro pages via vega-embed.
- **D-62** Every plan ships visualizations.
- **D-63** Hot-reload via atomic `.tmp+rename` writes to `viz/src/data/*.{json,geojson,vl.json}`.
- **D-64** Owner names: Phase 2 internal-only (Phase 3 owns publication decision).
- **D-65** Daniel's Law footprint isolation: owner names never leave `data/processed/` and `viz/src/data/`.
- **D-67** Single-command pipeline (`make all` or `bash scripts/run_phase2.sh`); fixed seeds.
- **D-68** `scripts/verify_phase2.py` smoke gate (exit 0/1).

### Claude's Discretion
- **D-56 (= D-55 in user-prompt numbering)** Berry "fair_bill" formula — researcher to recommend exact formula. Default-of-last-resort: Option (a) pure hedonic-predict.
- **D-66** `assessr::detect_chasing()` exact statistical test — researcher to extract from R source. Default-of-last-resort: Mann-Whitney U on (0.95, 1.05).
- The specific hedonic feature list, transforms, and interactions (within the post-ADP regime).

### Deferred Ideas (OUT OF SCOPE)
- Pre-ADP modeling (1989-2013).
- Causal/counterfactual analysis.
- Tax-appeal cohort analysis (Tier-C OPRS).
- Deed-level grantor-grantee network analysis.
- Spatial autocorrelation (PySAL).
- Public publication (Phase 3).
- Aggregate-only viz mode (Phase 3 may decide).

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **MODEL-01** | Generate neighborhood FE labels via k-means (k=5-8) on parcel centroids | §6.1 (k-means recipe with seed, scaling, silhouette) |
| **MODEL-02** | Hedonic OLS on 197 arms-length sales 2020-2025 with HC3 SEs, R² ≥ 0.7 | §1.2 (recommended spec); §6.2 (statsmodels HC3 syntax + prediction intervals) |
| **MODEL-03** | Apply hedonic to all 2,061 class-2 parcels; produce `estimated_true_value`; aggregate within 5% of $2.74B | §1.2 (out-of-sample prediction); §6.3 (calibration constant) |
| **CALC-01** | Berry tax-shift: `delta_i = actual_bill_i − fair_bill_i`; Σ delta ≈ 0 | §2 (full Berry formulas, both faithful and hedonic versions) |
| **CALC-02** | Tag each parcel with multi-tag `tenure_cohort` (per D-53) | §1.3 (tenure-tag construction recipe) |
| **CALC-03** | Cohort COD/PRD vs IAAO standards (COD ≤15%, PRD 0.98-1.03) | §3 (assessr::cod, prd, prb formulas verbatim from R source) |
| **TEST-01** | Reimplement assessr::detect_chasing(); TRUE/FALSE + CDF plot | §4 (full Python pseudocode port) |

---

## Project Constraints (from CLAUDE.md)

- **No notebooks** — Jupyter/Quarto categorically excluded. Use Python scripts under `scripts/` and `src/fairhaven_tax/models/`. Interactive viz goes in Astro under `viz/`. (PROJECT.md OUT-05 mentions a notebook but CLAUDE.md takes precedence; reproducibility goes through `scripts/run_phase2.sh` instead. Planner should explicitly note OUT-05 is satisfied by the script, not a notebook.)
- **/tmp BAN** — use `temporary_scripts/sandbox/` for scratch.
- **Daniel's Law** — owner names private; Phase 2 internal-only per D-64.
- **Python stack** — geopandas, statsmodels, scipy, scikit-learn, pdfplumber/camelot already in `pyproject.toml`. **`altair` is NOT yet in pyproject.toml — Wave 0 task: add `altair>=5.5,<7` to deps.**
- **GSD workflow enforcement** — all file edits via GSD commands (planner already covered).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Data validation gate | Python ETL (`scripts/validate_*.py`) | — | Reads parquet, writes parquet; no UI tier involved. |
| Hedonic model fitting | Python (`src/fairhaven_tax/models/hedonic.py`) | — | statsmodels lives in Python. |
| Berry tax-shift computation | Python (`src/fairhaven_tax/models/berry_shift.py`) | — | Pandas/numpy arithmetic. |
| IAAO ratio study | Python (`src/fairhaven_tax/models/ratio_study.py`) | — | Pure pandas; emits `ratio_study.parquet`. |
| CDF gap test | Python (`src/fairhaven_tax/models/cdf_gap_test.py`) | — | scipy.stats.ecdf + numpy. |
| Per-parcel JSON dump | Python serialization | Filesystem (atomic rename) | Modeling code writes; Astro file-watcher reads. |
| Chart specs (Vega-Lite JSON) | Altair (Python) | vega-embed (browser) | Altair generates JSON via `chart.save()`; vega-embed renders. |
| Map rendering | Browser (Leaflet client-side) | Astro static-build | Leaflet is a runtime-only library; Astro hydrates with `client:visible`. |
| Hot-reload trigger | Astro dev server's Vite file-watcher | Modeling code (atomic write side) | Vite watches `viz/src/data/*` by convention; modeling code emits via `.tmp+rename`. |
| Reproducibility orchestration | Shell script (`scripts/run_phase2.sh`) | Make (optional alias) | One bash file, deterministic seeds, POSIX exit codes. |
| Verification gate | Python (`scripts/verify_phase2.py`) | gsd-verifier | Reads expected artifacts, checks schemas, exit 0/1. |

---

## Standard Stack

### Core (Python — modeling)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **statsmodels** | 0.14.6 (latest, declared `>=0.14`) | OLS with HC3 robust SEs, prediction intervals | Canonical Python econometrics; `cov_type='HC3'` is the Berry-equivalent inference. [VERIFIED: PyPI 2026-04-29] |
| **scikit-learn** | 1.7.1 (installed; declared `>=1.5`) | k-means (`KMeans`) for neighborhood FE; StandardScaler | sklearn 1.5+ has `n_init='auto'` default; deterministic with `random_state`. [VERIFIED: pip list] |
| **scipy** | 1.15.3 (installed; declared `>=1.13`) | `scipy.stats.ecdf`, `scipy.stats.norm`, sample stats for CDF gap test | scipy.stats.ecdf added in 1.11+. [VERIFIED: pip list] |
| **pandas** | 2.3.3 (installed; declared `>=2.2`) | DataFrame backbone | already in use. [VERIFIED: pip list] |
| **geopandas** | 1.1.3 (latest; declared `>=1.0`) | Parcel geometries; reproject EPSG:3424 → 4326 for GeoJSON export | geopandas 1.x stable; `to_file(driver='GeoJSON')` is canonical export. [VERIFIED: PyPI 2026-04-29] |
| **pyarrow** | declared `>=17.0` | Parquet I/O (atomic) | already in use. [VERIFIED: pyproject.toml] |
| **altair** | 5.5.0 - 6.1.0 | Python → Vega-Lite spec generation | `chart.save("foo.vl.json", format="json")` produces vega-embed-compatible JSON directly. **Add to pyproject.toml — currently missing.** [VERIFIED: PyPI 2026-04-29] |

### Core (JS — Astro viz)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **astro** | 6.2.0 (latest stable as of 2026-04) | Static-site framework | D-59 lock; static output, file-watcher hot-reload. [VERIFIED: npm view astro 2026-04-29] |
| **leaflet** | 1.9.4 | Interactive parcel map | D-60 lock; pure-JS, no React/Svelte dependency. [VERIFIED: npm view leaflet 2026-04-29] |
| **vega-embed** | 7.1.0 | Render Vega-Lite JSON specs | D-61 lock; bundles vega + vega-lite + tooltip. [VERIFIED: npm view vega-embed 2026-04-29] |
| **@astrojs/preact** | latest | Preact integration (for Chart.tsx wrapper around vega-embed) | Lighter than React; vega-embed needs `useEffect`-style hook. [CITED: docs.astro.build/en/guides/integrations-guide/preact/] |
| **astro-leaflet** (community) | OPTIONAL — see §5 | Pre-baked Leaflet wrapper | Convenience; raw Leaflet via dynamic import is also fine. [CITED: github.com/pascal-brand38/astro-leaflet] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | declared | array math | always (transitive). |
| matplotlib | 3.10.8 (installed) | NOT for the public viz; only for ad-hoc EDA | scratch only — D-61 says Vega-Lite is the lock. |
| structlog | declared | structured logging in pipeline | wire into `scripts/run_phase2.sh`. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Astro (D-59 lock) | Plain HTML + Leaflet | Astro chosen for hot-reload + Phase 3 inheritance. Lock; do not revisit. |
| vega-embed | Plotly / Chart.js | D-61 lock. Altair generates Vega-Lite natively; any other chart lib forces re-translation. |
| statsmodels OLS HC3 | sklearn `LinearRegression` | sklearn lacks HC3 SEs entirely. Must use statsmodels. |
| k-means | DBSCAN / spatial clustering | k-means is what Berry-adjacent literature (Cook County CCAO) uses; DBSCAN unstable on small N=2,061. |
| Altair → Vega-Lite | Plotnine / matplotlib | D-61 lock. Altair's `to_json()` is byte-for-byte vega-embed-ingestible. |
| Berry sales-only fair-rate | Pure-hedonic Option (a) | **Run BOTH** — see §2. Berry is the public anchor; hedonic is the parcel-level artifact. |

**Installation:**
```bash
# Python — already configured EXCEPT altair
uv add 'altair>=5.5,<7'
# (everything else is in pyproject.toml; just `uv sync`)

# Astro viz scaffold (Plan 3 — to be created in viz/)
cd viz && npm create astro@latest -- --template minimal
npm install leaflet@1.9.4 vega-embed@7.1.0 @astrojs/preact preact
npx astro add preact
```

---

## Section 1: Berry / Cook County Methodology — Detailed Extraction

> **Critical clarification for the planner.** Berry has TWO distinct published works that this project conflates as "Berry's methodology." The planner (and discuss-phase) MUST treat them separately:
>
> **Work A — "Reassessing the Property Tax" (Feb 7, 2021, U Chicago Working Paper / SSRN abstract_id=3800536):** A nationwide regressivity-detection paper that runs a single regression on 26M Corelogic transactions: `ln(A_ijt / P_ijt) = α_jt + β·ln(P_ijt) + ε_ijt`. **This paper does NOT compute fair_bill or tax-shift dollars.** It only documents that β ≈ -0.34 nationally (assessment ratio falls 34% as price doubles within jurisdiction-year). [VERIFIED: paper text retrieved 2026-04-29, eq. (1) on p.11]
>
> **Work B — "Estimating Property Tax Shifting Due to Regressive Assessments: An Analysis of Chicago, 2011 to 2015" (March 15, 2018, Center for Municipal Finance research brief):** This is the source of the $2.235B headline figure. It defines the fair_tax / tax_shift formulas. [VERIFIED: brief retrieved 2026-04-29; URL https://propertytaxproject.uchicago.edu/files/2020/02/Tax-Shifting-Due-to-Regressive-Assessments.pdf which redirects to bpb-us-w2.wpmucdn.com]
>
> **Work B is the source for D-50 / D-55 / fair_bill formula.** Work A is the source for the regressivity-detection regression we should ALSO run as a robustness check.

### 1.1 Berry's published "fair_tax" / "tax_shift" formula (Work B, verbatim from the 2018 brief)

Berry's Section I.A "Estimating the tax shift" describes a **5-step procedure conducted separately for each year, within the sample of homes that have sold** [VERIFIED: 2018 brief p.1-2]:

> 1. **Estimate the total residential levy**, which is the sum of taxes due for all residential property tax bills (among the sample of properties that sold). Assume this is the total amount of taxes that must be raised from the residential tax base.
> 2. **Estimate the total value of the residential tax base**, which is the sum of the sale prices for all residential properties that sold. The key is that this step replaces the potentially flawed assessed value with the actual sale prices.
> 3. **Estimate the "fair tax rate"** as the aggregate residential levy divided by the aggregate residential tax base.
> 4. **Apply the fair tax rate to the sale price of each property** to get the "fair tax" for that property. This is the tax rate the property should have paid if (a) assessments were perfectly accurate, and (b) the levy was divided equally across properties in proportion to their value.
> 5. **Compute the difference between the fair tax and the actual tax** to get the "tax shift" for each property.

In compact algebra (subscript `i` = sold-property, `t` = year):

```
fair_rate_t = (Σ_{i ∈ sold_t}  actual_bill_i,t) / (Σ_{i ∈ sold_t}  sale_price_i,t)
fair_bill_i,t = fair_rate_t × sale_price_i,t                      # for sold i only
tax_shift_i,t = fair_bill_i,t − actual_bill_i,t                   # negative = under-taxed
```

By construction `Σ tax_shift_i = 0` within the sold sample. [VERIFIED: brief p.2]

### 1.2 Berry's extrapolation from sold sample to full population (Section I.B)

Berry explicitly says the simplest approach (assume sold = representative, multiply by `1/p` where p = sale rate) is OK in expectation. He uses **stratification with strata = (community area × class × assessed-value-quartile × year)** in the actual report and notes this is "the most conservative estimate of the tax shift compared to other alternatives." [VERIFIED: brief p.3]

For Fair Haven (one community, ~2,061 parcels, 197 sales over 6 years ≈ 33 sales/year average ≈ 1.6% sale rate per year, but 9.6% over the 6-year window), the analog is:
- Strata: `(neighborhood_FE_kmeans × assessed_value_quartile × sale_year)` or simpler `(neighborhood_FE × sale_year)` if quartile-strata get too thin.
- Weight `w_i = N_strata / n_sold_strata` for each sold parcel.
- Extrapolated tax shift in stratum s = `Σ_{i ∈ sold_s} w_i × tax_shift_i`.

### 1.3 Berry's hedonic — what does he actually use for property characteristics?

**He doesn't.** [VERIFIED: 2018 brief]. Berry's Cook County tax-shift report is a **sales-only sample-and-extrapolate** procedure. Property characteristics (sqft, beds, baths) appear nowhere in the formulas. The sale price IS the value estimate; that's the whole point — sale price is unbiased by definition, assessor's value is the suspect quantity.

The 2021 "Reassessing" paper (Work A) similarly does NOT use property characteristics. It uses jurisdiction-year FE and `ln(price)` only.

**Implication for this project:** Phase 2's hedonic that PROJECT.md / REQUIREMENTS.md MODEL-02 specifies (`log(sqft) + log(lot) + year_built + bedrooms + bathrooms + neighborhood_FE`) is **NOT a Berry replication**. It is a separate, complementary analysis.

**Why we should still run the hedonic:** Berry's procedure produces tax_shift estimates only for **sold properties** — for Fair Haven that's 197 parcels out of 2,061 (9.6%). The parcel-level Leaflet map (the public artifact) needs a `delta_dollars` value for ALL 2,061 parcels including the 1,864 unsold ones. The hedonic provides the imputation mechanism for the unsold majority.

### 1.4 Recommended dual-track approach

The planner MUST have plans for BOTH:

**Track 1 — Berry-faithful (the public anchor, satisfies D-50):**
1. Compute fair_rate per year on sold sample (197 sales, 6 years).
2. Compute tax_shift_i for sold parcels.
3. Stratify-and-extrapolate to all 2,061 parcels using `(neighborhood_FE × sale_year)` weights.
4. Headline figure: aggregate annual tax shift in dollars, decile distribution, by-tenure-cohort distribution.

**Track 2 — Hedonic Option-(a) (the parcel-level artifact):**
1. Fit hedonic on 197 sold sales (recommended spec below).
2. Predict `estimated_true_value_i` for all 2,061 parcels.
3. Compute `fair_bill_i = (estimated_true_value_i / Σ estimated_true_value) × total_levy_2025`.
4. Compute `actual_bill_i = current_assessment_i × tax_rate_2025` (use the verified $1.427/$100, not PROJECT.md's stale $1.574).
5. `delta_dollars_i = actual_bill_i − fair_bill_i`. By construction, `Σ delta_dollars = 0` after a constant-correction calibration step.
6. Headline figure: per-parcel delta, choropleth map.

**Reporting both is the disciplined move.** They should agree directionally; if they diverge sharply (e.g., Berry says +$300K cohort shift, hedonic says -$80K), document the discrepancy as a finding rather than picking one.

### 1.5 Recommended hedonic specification

Berry says nothing about hedonics; the spec we use is mass-appraisal-textbook standard (Gloudemans & Almy 2011, which Berry cites). Phase 1.5 unblocked the property-characteristic features via `prc.parquet`.

```
log(sale_price_i) ~ log(livable_area_i)
                  + log(lot_size_acres_i)
                  + year_built_i                        # or eff_age_i (PRC has both)
                  + bedrooms_i
                  + bathrooms_i                         # consider 0.5-bath weighting
                  + condition_i                         # ordinal
                  + quality_grade_i                     # ordinal
                  + C(neighborhood_FE_i, k=5..8)        # k-means on lat/lon centroid
                  + C(sale_year_i)                      # year FE per D-54
```

Notes:
- **Outcome `log(sale_price)` is canonical.** Multiplicative residuals (10% mispricing on a $500k home is 10% on a $2M home).
- **`log(livable_area)` and `log(lot_size_acres)` are canonical** for the same reason. Berry doesn't use them; mass-appraisal does.
- **Ordinal condition / quality_grade**: encode as integer (1=poor … 5=excellent) and treat as continuous to save degrees of freedom. With 197 obs and target ~12:1 obs:param ratio, we can afford ~16 parameters total. Tally: log_sqft (1) + log_lot (1) + year_built (1) + bedrooms (1) + bathrooms (1) + condition (1) + quality (1) + neighborhood FE (k-1, max 7) + year FE (5) = up to 18. **Tight but acceptable; consider dropping bedrooms (heavily collinear with sqft, expected VIF > 5) if VIF check fails.** [ASSUMED — needs VIF check on actual data]
- **Skip waterfront flag, fireplaces, garage, etc.** Phase 1.5 captured them but each adds a parameter at marginal R² gain. Try them in robustness; not in the headline spec. [ASSUMED]
- **HC3 robust SEs** are textbook for small-sample heteroskedasticity (MacKinnon & White 1985). statsmodels syntax: `model.fit(cov_type='HC3')`.
- **Year FE absorbs pandemic vs post-pandemic price-level differences (D-54).**
- **R² target ≥ 0.7** per REQUIREMENTS.md MODEL-02. Achievable on residential hedonics with this feature set per published literature [CITED: Sirmans et al. 2008 meta-analysis of hedonic R² in single-family residential].

### 1.6 How Berry handles parcels that did NOT sell

Berry's core procedure (Work B) **ignores them in the fair-rate calculation entirely**. He addresses them only via stratified reweighting in the extrapolation step (§1.2 above), which scales sample-level dollar shifts to population-level estimates without ever assigning a per-parcel shift to an unsold parcel.

The 2021 paper (Work A) sidesteps this entirely — it's a regressivity-detection regression run on the sold sample only and never claims to estimate per-unsold-parcel anything.

**This is why we need the hedonic — it's the only way to put a `delta_dollars` on an unsold parcel.** [VERIFIED: 2018 brief, 2021 paper]

### 1.7 Berry's time-window choice

5 calendar years (2011-2015), one annual fair-rate per year. [VERIFIED: brief p.3 Table 1 shows separate `Tax Shift` row per year 2011-2015]. This justifies our 6-year window 2020-2025.

### 1.8 Berry's headline numbers (calibration anchor)

| Year | Aggregate annual tax shift | % of total residential levy* |
|------|---------------------------|------------------------------|
| 2011 | $723,000,000 | ~5% |
| 2012 | $435,000,000 | ~3% |
| 2013 | $350,000,000 | ~3% |
| 2014 | $434,000,000 | ~3% |
| 2015 | $293,000,000 | ~2% |
| **Total** | **$2,235,000,000** | — |

*Residential levy in Cook County ≈ $14B/year. Sources: Civic Federation 2017.

**Top decile under-taxed by ~$800M / $2.235B ≈ 36% of the total shift. Bottom 7 deciles absorbed it.** [VERIFIED: brief p.4-5 Figures 1-4]

**Translated to Fair Haven scale:** Total annual residential levy ≈ $40.34M (DLGS 2025, all classes; class-2 share ≈ 97% so ≈ $39M). A material annual tax shift would be **$1-2M** if we naively scale Cook's 2-5% rate. The PROJECT.md decision-gate threshold of $200K cohort-correlated is conservative (~0.5% of levy) — easily clearable if any signal at all exists.

### 1.9 Berry's published visualization patterns (we will replicate via Altair)

[VERIFIED: 2018 brief Figures 1-4]:
1. **Figure 1: Binned scatter — proportion over/under-paying by sale-price decile.** Two-line chart, x-axis = decile centroid sale price, y-axis = proportion. Two series: under-paying (blue), over-paying (red).
2. **Figure 2: Net Tax Shift by Sale Price Decile.** Bar chart, x-axis = decile 1-10, y-axis = $ millions. Negative bars at decile 10.
3. **Figure 3: Fair Taxes vs. Actual Taxes, by Sale Price Decile.** Side-by-side bar chart per decile.
4. **Figure 4: Percentage of Taxes Over/Under Paid by Sale Price Decile.** Bar chart, percentages.

Plus the hedonic-driven choropleth (NOT in Berry's brief; the unique Fair Haven artifact):
5. **Parcel choropleth on `delta_dollars`** with diverging color centered at zero (D-60).
6. **Cohort tag overlay** — color parcels by tenure tag.
7. **Residual scatter** from hedonic — `predicted_value` vs `sale_price`, 45° line.
8. **CDF of assessment-to-sale ratio** with cliff annotation (the canonical CDF gap test plot, D-66).

---

## Section 2: Recommended Berry tax-shift implementation (Python)

```python
# src/fairhaven_tax/models/berry_shift.py
import pandas as pd
import numpy as np

def berry_fair_rate_per_year(sales: pd.DataFrame) -> pd.DataFrame:
    """Berry-faithful fair-rate computation (Work B, 2018 CMF brief).

    Args:
        sales: DataFrame with columns ['pams_pin','sale_year','sale_price',
               'actual_bill_at_sale_year']. Filter to arms-length only upstream.

    Returns:
        DataFrame indexed by sale_year with columns
        ['levy_total','base_total','fair_rate','n_sales'].
    """
    g = sales.groupby('sale_year').agg(
        levy_total=('actual_bill_at_sale_year','sum'),
        base_total=('sale_price','sum'),
        n_sales=('pams_pin','size'),
    )
    g['fair_rate'] = g['levy_total'] / g['base_total']
    return g.reset_index()


def berry_per_parcel_shift_sold(sales: pd.DataFrame, fair_rates: pd.DataFrame) -> pd.DataFrame:
    """Per-sold-parcel fair_bill, tax_shift (Berry Work B steps 4-5)."""
    df = sales.merge(fair_rates[['sale_year','fair_rate']], on='sale_year')
    df['fair_bill']  = df['fair_rate'] * df['sale_price']
    df['tax_shift']  = df['fair_bill'] - df['actual_bill_at_sale_year']
    # Sanity: within each year, sum should be zero.
    return df


def berry_extrapolate(sold_shifts: pd.DataFrame, parcels_universe: pd.DataFrame,
                      strata_cols=('neighborhood_fe','sale_year')) -> pd.DataFrame:
    """Stratified reweighting to scale sold-sample shifts to full population.

    Strata = combination of strata_cols. Weight = N_strata / n_sold_strata.
    """
    n_sold = sold_shifts.groupby(list(strata_cols)).size().rename('n_sold')
    n_total = parcels_universe.groupby(list(strata_cols)).size().rename('n_total')
    weights = (n_total / n_sold).rename('weight').reset_index()
    out = sold_shifts.merge(weights, on=list(strata_cols), how='left')
    out['weighted_shift'] = out['tax_shift'] * out['weight']
    return out
```

```python
# Hedonic Option-(a) per-parcel delta — for the public choropleth
def hedonic_per_parcel_delta(parcels: pd.DataFrame, total_levy: float,
                             tax_rate_per_100: float = 1.427) -> pd.DataFrame:
    """Compute fair_bill from estimated_true_value across full parcel universe.

    parcels must have ['pams_pin','assessed_value','estimated_true_value'].
    """
    # Calibration: if Σ estimated_true_value ≠ DLGS-published net valuation,
    # apply a constant scalar so fair_bill aggregates to the actual levy.
    p = parcels.copy()
    scale = total_levy / p['estimated_true_value'].sum()
    p['fair_bill']      = p['estimated_true_value'] * scale
    p['actual_bill']    = p['assessed_value'] * (tax_rate_per_100 / 100.0)
    p['delta_dollars']  = p['actual_bill'] - p['fair_bill']
    # Σ delta_dollars should be near 0 if assessor's aggregate matches DLGS.
    assert abs(p['delta_dollars'].sum()) < 0.01 * total_levy, "delta sum off by >1% of levy"
    return p
```

**Critical: use the verified tax rate $1.427/$100, NOT PROJECT.md's stale $1.574.** REQUIREMENTS.md DATA-02 documents this correction explicitly.

---

## Section 3: IAAO ratio-study formulas (verbatim from assessr R source)

[VERIFIED: ccao-data/assessr `R/formulas.R` retrieved 2026-04-29 from raw.githubusercontent.com]

### 3.1 COD (Coefficient of Dispersion)

> COD is the average absolute percent deviation from the median ratio. It is a measure of horizontal equity in assessment.

```python
def cod(ratio: np.ndarray) -> float:
    """COD per IAAO Standard on Ratio Studies (April 2013) §9.1.

    ratio = estimated_fair_market_value / sale_price (i.e., the assessor's
    sale ratio). IAAO recommends trimming beyond 3*IQR before computing.
    """
    ratio = np.asarray(ratio, dtype=float)
    ratio = ratio[~np.isnan(ratio)]
    med = np.median(ratio)
    return (np.mean(np.abs(ratio - med)) / med) * 100.0

def cod_met(x: float) -> bool:
    """IAAO acceptable range: 5 ≤ COD ≤ 15."""
    return 5.0 <= x <= 15.0
```

[VERIFIED: assessr formulas.R lines 25-65, `cod_met` line 251]

### 3.2 PRD (Price-Related Differential)

> PRD is the mean ratio divided by the mean ratio weighted by sale price. Vertical equity. PRD centers slightly above 1; generally accepted 0.98-1.03 per IAAO §9.2.7.

```python
def prd(assessed: np.ndarray, sale_price: np.ndarray) -> float:
    a = np.asarray(assessed, dtype=float)
    p = np.asarray(sale_price, dtype=float)
    mask = ~(np.isnan(a) | np.isnan(p))
    a, p = a[mask], p[mask]
    ratio = a / p
    return ratio.mean() / np.average(ratio, weights=p)

def prd_met(x: float) -> bool:
    return 0.98 <= x <= 1.03
```

[VERIFIED: assessr formulas.R lines 80-117, `prd_met` line 256]

### 3.3 PRB (Price-Related Bias) — IAAO recommends over PRD

> PRB is a different approach to measuring fairness across homes with different sale prices. Centered around 0; acceptable -0.05 to 0.05. Less sensitive to outliers than PRD.

The R source `calc_prb`:

```r
calc_prb <- function(assessed, sale_price) {
  ratio <- assessed / sale_price
  med_ratio <- stats::median(ratio)
  lhs <- (ratio - med_ratio) / med_ratio
  rhs <- log(((assessed / med_ratio) + sale_price) * 0.5) / log(2)
  prb_model <- stats::lm(formula = lhs ~ rhs)
  prb_model
}
```

Python port:

```python
import statsmodels.api as sm

def prb(assessed: np.ndarray, sale_price: np.ndarray) -> float:
    a = np.asarray(assessed, dtype=float)
    p = np.asarray(sale_price, dtype=float)
    mask = ~(np.isnan(a) | np.isnan(p))
    a, p = a[mask], p[mask]
    ratio = a / p
    med = np.median(ratio)
    lhs = (ratio - med) / med
    rhs = np.log(((a / med) + p) * 0.5) / np.log(2)
    rhs = sm.add_constant(rhs)
    model = sm.OLS(lhs, rhs).fit()
    return float(model.params[1])

def prb_met(x: float) -> bool:
    return -0.05 <= x <= 0.05
```

[VERIFIED: assessr formulas.R lines 122-160, `prb_met` line 261]

### 3.4 Sales chasing acceptable threshold

[VERIFIED: assessr ratio-study vignette]: ≤ 5% of ratios in the sales-chased zone is the acceptable threshold (i.e., the `cdf_gap` of 0.03 default with bounds (0.98, 1.02) is the LIMIT — exceeding it means chasing is detected).

### 3.5 IAAO outlier-trimming convention

> NOTE: The IAAO recommends trimming outlier ratios before calculating COD, as it is extremely sensitive to large outliers. The typical method used is dropping values beyond 3 * IQR (inner-quartile range). See IAAO Standard on Ratio Studies Appendix B.1.

[VERIFIED: assessr formulas.R lines 9-15, roxygen]

---

## Section 4: assessr::detect_chasing() Python port (TEST-01)

[VERIFIED: ccao-data/assessr `R/sales_chasing.R` retrieved 2026-04-29 from raw.githubusercontent.com]

The R reference implementation has three functions: `detect_chasing` (orchestrator), `detect_chasing_cdf` (CDF gap method), `detect_chasing_dist` (distribution comparison). The orchestrator AND-combines the two when `method='both'` (the default).

### 4.1 Full Python port

```python
# src/fairhaven_tax/models/cdf_gap_test.py
"""Python port of CCAO assessr::detect_chasing().

Source: https://github.com/ccao-data/assessr/blob/master/R/sales_chasing.R
Retrieved 2026-04-29 commit master.

NOT a statistical test (no p-value). It returns TRUE/FALSE based on
two heuristic signatures of selective reappraisal ("sales chasing").
"""
import numpy as np
from typing import Tuple
import warnings

def detect_chasing_cdf(ratio: np.ndarray,
                       bounds: Tuple[float, float] = (0.98, 1.02),
                       cdf_gap: float = 0.03) -> bool:
    """CDF discontinuity method.

    Returns TRUE iff:
      - The maximum gap in the empirical CDF (max diff between consecutive
        sorted ratios' percentile ranks) exceeds `cdf_gap`, AND
      - That gap occurs at a ratio value strictly inside `bounds`.

    Default cdf_gap=0.03 means "≥3% of ratios share the same value."
    Default bounds=(0.98, 1.02) is the "near-1.0" zone of suspicion.
    """
    assert 0 < cdf_gap < 1
    sorted_ratio = np.sort(ratio[~np.isnan(ratio)])
    if len(sorted_ratio) < 2:
        return False
    # ECDF values at each sorted point: 1/n, 2/n, ..., n/n
    n = len(sorted_ratio)
    cdf = np.arange(1, n + 1) / n
    diffs = np.diff(cdf)
    if len(diffs) == 0:
        return False
    idx = int(np.argmax(diffs))
    diff_loc = float(sorted_ratio[idx])
    return bool(diffs[idx] > cdf_gap and bounds[0] < diff_loc < bounds[1])


def detect_chasing_dist(ratio: np.ndarray,
                        bounds: Tuple[float, float] = (0.98, 1.02),
                        n_sim: int = 10_000,
                        rng: np.random.Generator = None) -> bool:
    """Distribution-comparison method (IAAO Standard Appendix E §4).

    Compares fraction of ACTUAL ratios in `bounds` to fraction expected
    under a normal distribution with the same mean and sd. Returns TRUE
    iff actual concentration > ideal concentration (i.e., "bunched").

    Note: original R uses rnorm(n=10000) — non-deterministic. We accept
    a `rng` for reproducibility per D-67.
    """
    if rng is None:
        rng = np.random.default_rng(seed=42)
    r = ratio[~np.isnan(ratio)]
    if len(r) < 2:
        return False
    mu, sigma = float(np.mean(r)), float(np.std(r, ddof=1))
    ideal = rng.normal(mu, sigma, size=n_sim)
    pct_ideal  = float(np.mean((ideal >= bounds[0]) & (ideal <= bounds[1])))
    pct_actual = float(np.mean((r     >= bounds[0]) & (r     <= bounds[1])))
    return pct_actual > pct_ideal


def detect_chasing(ratio: np.ndarray,
                   method: str = 'both',
                   bounds: Tuple[float, float] = (0.98, 1.02),
                   cdf_gap: float = 0.03,
                   rng: np.random.Generator = None) -> bool:
    """Orchestrator. method ∈ {'cdf','dist','both'}; 'both' AND-combines.

    Mirrors assessr::detect_chasing default behavior.
    """
    assert method in ('cdf', 'dist', 'both')
    r = np.asarray(ratio, dtype=float)
    if r.size <= 2:
        raise ValueError("Need length(ratio) > 2")
    if r.size < 30:
        warnings.warn(
            "Sales chasing detection can be misleading when applied to small "
            "samples (N < 30). Increase N or use a different statistical test."
        )
    if method == 'cdf':
        return detect_chasing_cdf(r, bounds=bounds, cdf_gap=cdf_gap)
    if method == 'dist':
        return detect_chasing_dist(r, bounds=bounds, rng=rng)
    return (detect_chasing_cdf(r, bounds=bounds, cdf_gap=cdf_gap)
            and detect_chasing_dist(r, bounds=bounds, rng=rng))
```

### 4.2 Critical implementation notes

1. **In R, `stats::ecdf(sorted_ratio)(sorted_ratio)` returns `1/n, 2/n, ..., n/n`** — the trailing percentile is 1.0. The Python `np.arange(1, n+1)/n` matches this exactly. **Do NOT use `scipy.stats.ecdf` and call it on the same points — that builds a step function with potentially different step boundaries.** [VERIFIED: R source shows `cdf <- stats::ecdf(sorted_ratio)(sorted_ratio)` evaluates ECDF AT the sorted points themselves]
2. **Both methods must be TRUE for `method='both'` to return TRUE.** This is conservative — fewer false positives. Per the R source: `detect_chasing_cdf(ratio, ...) & detect_chasing_dist(ratio, na.rm = na.rm, ...)`. [VERIFIED]
3. **The 30-observation warning fires below N=30 but does NOT short-circuit.** Fair Haven 2020-2025 has 197 sales — well above the threshold. By cohort, smaller subsets may dip below 30; the function will still execute but emit a warning. [VERIFIED]
4. **Determinism risk: the `dist` method calls `rnorm(n=10000)` in R without a fixed seed.** Our port MUST accept an `rng` parameter and the Phase 2 pipeline MUST seed it (D-67). Otherwise the TRUE/FALSE result can flip between runs at the boundary.
5. **The ratio convention.** assessr docstring says "numerator = estimated fair market value, denominator = actual sale price." For the IAAO/CCAO sales-chasing test, the ratio is the **assessor-side estimate divided by the market price**. In Fair Haven's case, that's `sale_assessment / sale_price` — exactly what Bloustein's `sale_assessment` column gives us at time-of-sale (D-55, REQUIREMENTS.md TEST-01). DO NOT invert.

### 4.3 The canonical "cliff plot" (TEST-01 deliverable)

```python
# scripts/build_cdf_gap_test.py — emits viz/src/data/charts/cdf_gap_test.vl.json
import altair as alt, pandas as pd, numpy as np

def cdf_cliff_chart(ratios: np.ndarray, verdict: bool, jurisdiction: str = 'Fair Haven') -> alt.Chart:
    sorted_r = np.sort(ratios[~np.isnan(ratios)])
    cdf = np.arange(1, len(sorted_r)+1) / len(sorted_r)
    df = pd.DataFrame({'ratio': sorted_r, 'cdf': cdf})
    base = alt.Chart(df).mark_line(strokeWidth=2).encode(
        x=alt.X('ratio:Q', scale=alt.Scale(domain=[0.5,1.5]),
                title='Sales Ratio (assessment / sale_price)'),
        y=alt.Y('cdf:Q',  title='Empirical CDF'),
    )
    band = alt.Chart(pd.DataFrame({'lo':[0.98],'hi':[1.02]})).mark_rect(
        opacity=0.15, color='red'
    ).encode(x='lo:Q', x2='hi:Q')
    title = f'CDF Gap Test — {jurisdiction} — Sales Chasing: {"DETECTED" if verdict else "not detected"}'
    return alt.layer(band, base).properties(title=title, width=720, height=320)
```

Save with `chart.save('viz/src/data/charts/cdf_gap_test.vl.json', format='json')`. [VERIFIED: altair.Chart.save with format='json' produces vega-embed-compatible spec; PyPI altair 6.1 docs]

---

## Section 5: Astro + Leaflet + Vega-Lite integration patterns

### 5.1 Recommended structure

```
viz/
├── astro.config.mjs
├── package.json                    # astro@6.2, leaflet@1.9.4, vega-embed@7.1, @astrojs/preact
├── public/
│   └── leaflet/                    # icon assets — copied from node_modules per known pitfall
│       ├── marker-icon.png
│       └── marker-shadow.png
└── src/
    ├── components/
    │   ├── ParcelMap.astro         # raw <div> + dynamic-import script — see 5.2
    │   ├── Chart.tsx               # Preact wrapper around vega-embed — see 5.3
    │   └── ParcelPopup.astro       # popup template, reads overlay JSONs
    ├── data/                       # PYTHON WRITES HERE; Vite watches
    │   ├── parcels.geojson         # base layer (D-60)
    │   ├── overlays/
    │   │   ├── delta_dollars.json
    │   │   ├── assessment_ratio.json
    │   │   └── tenure_cohort.json
    │   └── charts/
    │       ├── hedonic_residuals.vl.json
    │       ├── cdf_gap_test.vl.json
    │       ├── cohort_box.vl.json
    │       └── data_quality.vl.json
    └── pages/
        ├── index.astro             # landing
        ├── data-quality.astro
        ├── hedonic.astro
        ├── tax-shift.astro
        ├── ratio-study.astro
        └── cdf-gap-test.astro
```

### 5.2 `ParcelMap.astro` — raw Leaflet, no wrapper library

```astro
---
// src/components/ParcelMap.astro
const { overlay = 'delta_dollars', height = '80vh' } = Astro.props;
---
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<div id="parcel-map" style={`height: ${height}; width: 100%;`}></div>

<script type="module" define:vars={{ overlay }}>
  import L from 'leaflet';

  const map = L.map('parcel-map').setView([40.3608, -74.0426], 15); // Fair Haven center
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap', maxZoom: 19,
  }).addTo(map);

  const [parcels, ovr] = await Promise.all([
    fetch('/src/data/parcels.geojson').then(r => r.json()),
    fetch(`/src/data/overlays/${overlay}.json`).then(r => r.json()),
  ]);

  // Diverging color centered at zero (delta_dollars convention)
  const values = Object.values(ovr);
  const max = Math.max(...values.map(Math.abs));
  const color = (v) => {
    const t = v / max; // [-1, 1]
    if (t > 0) return `rgba(220,${Math.round(180*(1-t))},${Math.round(180*(1-t))},0.7)`; // red = over
    return `rgba(${Math.round(180*(1+t))},${Math.round(180*(1+t))},220,0.7)`;            // blue = under
  };

  L.geoJSON(parcels, {
    style: f => ({
      color: '#444', weight: 0.5,
      fillColor: color(ovr[f.properties.PAMS_PIN] ?? 0),
      fillOpacity: 0.7,
    }),
    onEachFeature: (f, layer) => {
      const pin = f.properties.PAMS_PIN;
      const v = ovr[pin];
      layer.bindPopup(`<b>${pin}</b><br/>${overlay}: ${v?.toLocaleString?.() ?? 'n/a'}`);
    },
  }).addTo(map);
</script>
```

**Why this pattern over `astro-leaflet`:** the wrapper packages (e.g., pascal-brand38/astro-leaflet) bundle opinions about default tile layers and SSR behavior. A raw `<script type="module">` block is ~30 lines, has zero dependency churn, and is easy to debug. Use the wrapper packages only if Plan 3 timeline pressure justifies it. [CITED: github.com/pascal-brand38/astro-leaflet]

**Known pitfall:** Leaflet's marker icons are loaded by relative path at runtime; Vite tree-shakes them. **Copy `marker-icon.png`, `marker-icon-2x.png`, `marker-shadow.png` from `node_modules/leaflet/dist/images/` to `viz/public/leaflet/` and set `L.Icon.Default.imagePath = '/leaflet/'`.** [CITED: roblabs/maps-withastro README]

### 5.3 `Chart.tsx` — Preact wrapper for vega-embed

```tsx
// src/components/Chart.tsx
import { useEffect, useRef } from 'preact/hooks';
import vegaEmbed from 'vega-embed';

interface ChartProps {
  spec: string;            // path to .vl.json under src/data/charts/
  height?: number;
  width?: number;
}

export default function Chart({ spec, height = 320, width = 720 }: ChartProps) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    fetch(spec).then(r => r.json()).then(json => {
      vegaEmbed(ref.current!, json, {
        actions: false, renderer: 'canvas',
      });
    });
  }, [spec]);
  return <div ref={ref} style={{ height, width, maxWidth: '100%' }} />;
}
```

Used in a page:

```astro
---
import Chart from '../components/Chart.tsx';
import ParcelMap from '../components/ParcelMap.astro';
---
<ParcelMap overlay="delta_dollars" />
<Chart spec="/src/data/charts/cdf_gap_test.vl.json" client:visible />
```

**Why `client:visible` not `client:load`:** `client:visible` defers vega-embed JS bundle (~280KB minified) until the chart scrolls into view. `client:load` would block initial paint. For map: it MUST be `client:load` (or no directive at all if using raw `<script type="module">` as in 5.2 — which executes synchronously after parse). [CITED: docs.astro.build/en/reference/directives-reference/]

### 5.4 Hot-reload contract (D-63)

Astro/Vite watches `src/**/*` by default. Writing to `src/data/*.json` from Python triggers a full-page reload of any open browser tab. **Atomic write is mandatory** — Vite's watcher fires on filesystem events; a partial-write JSON crashes the page.

Python pattern (matches existing `src/fairhaven_tax/persist/parquet_io.py` convention):

```python
import os, json, tempfile
from pathlib import Path

def atomic_write_json(payload: dict | list, path: Path) -> None:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False, suffix='.tmp') as tmp:
        json.dump(payload, tmp)
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)  # POSIX-atomic rename

def atomic_save_chart(chart, path: Path) -> None:
    """Altair chart -> .vl.json, atomic."""
    spec = chart.to_dict()  # vega-embed-compatible
    atomic_write_json(spec, path)
```

[CITED: altair docs `to_dict()` returns the same JSON as `save(format='json')`; the latter just wraps the former + writes]

### 5.5 Vega-Lite 5000-row inline-data limit

[CITED: altair-viz.github.io/user_guide/large_datasets.html]: charts with > 5,000 rows of inline data raise `MaxRowsError`. Fair Haven sales = 197 (no risk). Per-parcel residuals = 2,061 (no risk). Per-parcel-by-year time series = 80,329 — **AT RISK**. Workarounds:
1. Use `alt.data_transformers.disable_max_rows()` if data must be inline.
2. Better: write data as a separate JSON file and reference by URL: `alt.Chart('/src/data/timeseries.json').mark_line()...` — let vega-embed fetch lazily.

For our case, only the cohort time-series chart hits this; the planner should default to URL-based data references for any chart over ~1,000 rows.

---

## Section 6: Statistical implementation notes

### 6.1 k-means neighborhood FE (MODEL-01)

```python
# src/fairhaven_tax/models/neighborhood_fe.py
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
import numpy as np, pandas as pd

def assign_neighborhood_fe(parcels: pd.DataFrame,
                           xy_cols=('centroid_x_3424', 'centroid_y_3424'),
                           k_range=range(5, 9),
                           seed: int = 42) -> tuple[pd.DataFrame, int]:
    """k-means on parcel centroids in NJ State Plane (EPSG:3424, US ft).

    Returns (parcels_with_fe, best_k). Picks k by silhouette score.

    Uses NJ State Plane (NOT lat/lon WGS84) so distance metric is in feet.
    Reproject only at GeoJSON-export boundary (per D-60, parcels.parquet
    is already EPSG:3424).
    """
    X = parcels[list(xy_cols)].to_numpy(dtype=float)
    X = StandardScaler().fit_transform(X)
    best_k, best_score = None, -np.inf
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=seed, n_init=10).fit(X)
        s = silhouette_score(X, km.labels_)
        if s > best_score:
            best_k, best_score, best_labels = k, s, km.labels_
    out = parcels.copy()
    out['neighborhood_fe'] = best_labels
    return out, best_k
```

**Notes:**
- **`random_state=42` mandatory per D-67** (seed determinism).
- **Centroids must be in EPSG:3424 (US ft)** for k-means distance to mean physical-distance. Phase 1 stores parcels in 3424. Reproject ONLY at the `to_file('parcels.geojson', driver='GeoJSON')` boundary (which also requires EPSG:4326 per Leaflet).
- **`n_init=10` (or 'auto' which defaults to 10 in sklearn 1.5+)** — multiple random restarts mitigate local-minimum sensitivity.
- **Silhouette in `range(5,9)`** matches D-54's k ∈ {5..8}.
- **StandardScaler before k-means** is critical — x and y differ by orders of magnitude in raw US ft; without scaling, clusters become 1D.
- Skip including style/age/value features. The whole point of "neighborhood" FE is *spatial* heterogeneity. Adding style features double-counts the property characteristics already in the hedonic.

### 6.2 statsmodels OLS with HC3 + prediction intervals

```python
# src/fairhaven_tax/models/hedonic.py
import statsmodels.api as sm
import statsmodels.formula.api as smf
import pandas as pd, numpy as np

HEDONIC_FORMULA = (
    "np.log(sale_price) ~ np.log(livable_area) + np.log(lot_size_acres) "
    "+ year_built + bedrooms + bathrooms + condition_ord + quality_grade_ord "
    "+ C(neighborhood_fe) + C(sale_year)"
)

def fit_hedonic(sales: pd.DataFrame):
    model = smf.ols(HEDONIC_FORMULA, data=sales).fit(cov_type='HC3')
    # Sanity gates per REQUIREMENTS.md MODEL-02
    assert model.rsquared >= 0.7, f"R² = {model.rsquared:.3f} below target 0.7"
    return model

def predict_with_intervals(model, parcels: pd.DataFrame, alpha: float = 0.05):
    """Out-of-sample prediction WITH prediction intervals (not CI).

    Prediction intervals account for irreducible noise in y; CI is for the mean.
    For per-parcel value imputation we want PI.

    Note: HC3 affects coefficient SEs, not the residual variance used for PI.
    statsmodels' get_prediction returns the OLS-based PI by default.
    """
    pred = model.get_prediction(parcels)
    summary = pred.summary_frame(alpha=alpha)
    # Columns: mean, mean_se, mean_ci_lower, mean_ci_upper,
    #          obs_ci_lower, obs_ci_upper  <- PI
    parcels = parcels.copy()
    parcels['log_pred']     = summary['mean']
    parcels['log_pi_lower'] = summary['obs_ci_lower']
    parcels['log_pi_upper'] = summary['obs_ci_upper']
    parcels['estimated_true_value'] = np.exp(parcels['log_pred'])
    return parcels
```

**Pitfalls:**
- **Smearing factor for log-OLS back-transform.** `exp(mean(log y))` is biased low. Standard correction: multiply by `exp(σ²/2)` where σ² = MSE. Apply ONLY when you want unbiased levels; for the choropleth, this is a constant scalar that gets absorbed by the calibration step in §2's `hedonic_per_parcel_delta` so it does not change the per-parcel ranking. **Document but don't apply unless VIF check shows it matters.** [CITED: Wooldridge "Introductory Econometrics" §6.4]
- **VIF check.** With `bedrooms` + `log(livable_area)` + `bathrooms` likely collinear, run `from statsmodels.stats.outliers_influence import variance_inflation_factor`. Drop any feature with VIF > 10. [CITED: statsmodels.stats.outliers_influence]
- **Cluster-robust SEs (alternative to HC3).** If neighborhood FE residuals show within-cluster correlation, use `cov_type='cluster', cov_kwds={'groups': df['neighborhood_fe']}`. With only 5-8 clusters, this can be unstable; 30+ clusters preferred. **Stay with HC3 unless residual diagnostics demand otherwise.** [CITED: Cameron & Miller "A Practitioner's Guide to Cluster-Robust Inference" 2015]

### 6.3 Aggregate calibration constant (MODEL-03 ±5% gate)

REQUIREMENTS.md MODEL-03 gate: aggregate predicted true value within 5% of $2.74B (real measured class-2 only). If hedonic predicts $2.50B aggregate, apply scalar `c = 2.74e9 / 2.50e9 = 1.096` to all predictions. **This scalar is mathematically identical to the calibration step in `hedonic_per_parcel_delta` (§2) — they multiply through to the same `fair_bill`. Document the constant but verify the calibration logic only happens once.**

### 6.4 Ratio-study denominator for CDF gap test (TEST-01)

Per D-55 and REQUIREMENTS.md TEST-01: ratio = `sale_price / sale_assessment_at_year_of_sale` (NOT `sale_price / current_assessment`). The Bloustein `modiv_history.parquet` `sale_assessment` column is the gold-standard denominator. Joining: `sales.parquet` rows × `modiv_history.parquet` filtered to `(parcel_pin, sale_year)` and projecting `sale_assessment`.

**Direction-of-ratio convention check:** assessr docstring: "numerator = estimated fair market value, denominator = actual sale price" → ratio = `assessment / sale_price`. So **sale_assessment / sale_price**, not the inverse. A "chased" ratio is one where assessor's number got dragged toward the sale price → ratio cluster at 1.0 → cliff at the right edge of (0.98, 1.02).

### 6.5 Multi-tag tenure cohorts (CALC-02 / D-53)

```python
# src/fairhaven_tax/models/tenure_cohorts.py
import pandas as pd
from datetime import date

def assign_tenure_tags(parcels: pd.DataFrame,
                       sales_long: pd.DataFrame,  # arms-length only, all years 1989+
                       modiv_history: pd.DataFrame,
                       ) -> pd.DataFrame:
    """Multi-tag assignment per D-53. Returns parcels with a 'tenure_tags' list column."""
    last_armslength = (sales_long
                       .sort_values('sale_date')
                       .groupby('pams_pin').tail(1)
                       .set_index('pams_pin')['sale_date'])
    fam_only = (sales_long.groupby('pams_pin')['nu_code']
                .apply(lambda s: s.notna().any() and not (s.isna() | (s == '00')).any()))
    # never_sold: no row in sales_long since 1989
    has_armslength_since_1989 = sales_long['pams_pin'].unique()

    def tags(pin):
        out = []
        if pin not in has_armslength_since_1989:
            out.append('never_sold')
            out.append('tenure_pre_2015')  # implied per D-53
        else:
            d = last_armslength[pin]
            if   d.year < 2015: out.append('tenure_pre_2015')
            elif d.year < 2020: out.append('tenure_2015_2019')
            elif d.year < 2023: out.append('tenure_pandemic_2020_2022')
            else:               out.append('tenure_post_pandemic_2023plus')
        if fam_only.get(pin, False):
            out.append('family_sale_only')
        return out

    p = parcels.copy()
    p['tenure_tags'] = p['pams_pin'].map(tags)
    return p
```

**Storage in parquet:** list-of-strings column. Polars/DuckDB tolerate it; pyarrow round-trips it. For the Astro overlay JSON, flatten to a per-tag boolean dict: `{pams_pin: {'never_sold': true, 'tenure_pre_2015': true, ...}}`. The Leaflet popup reads any tag the user filters by.

---

## Section 7: Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OLS coefficients with robust SEs | numpy normal equations + manual White SE | `statsmodels.api.OLS(...).fit(cov_type='HC3')` | HC3 small-sample correction is tricky; statsmodels has the canonical implementation. |
| Empirical CDF | manual sort + cumulative count | `np.arange(1, n+1)/n` after `np.sort` (matches R's stats::ecdf evaluated at sample points) | Off-by-one errors on the boundary; assessr's reference uses this exact convention. |
| k-means clustering | manual EM loop | `sklearn.cluster.KMeans(random_state=42, n_init=10)` | Reproducible seeded init; multiple restarts already in. |
| Atomic file write | `open('w'); write` | `tempfile.NamedTemporaryFile + os.replace` (already in `parquet_io.py`) | Vite watcher fires on partial writes; corrupts hot-reload. |
| Vega-Lite spec from scratch | hand-write JSON | `altair.Chart(...).save('foo.vl.json', format='json')` | Altair is officially the Python frontend; output is byte-for-byte vega-embed-compatible. |
| Choropleth color scale | manual RGB interpolation | `d3-scale-chromatic` `d3.interpolateRdBu` (npm) OR delegate via Leaflet `L.geoJSON({style: ...})` with a small custom function | Diverging palette centered at zero needs a symmetric domain; chroma libraries handle that correctly. |
| Stratified reweighting | manual groupby loop | pandas `merge` + arithmetic per `berry_extrapolate()` in §2 | Standard pattern; do not bring in survey-sampling libraries (overkill). |
| GeoJSON serialization | manual JSON construction from shapely | `geopandas.GeoDataFrame.to_file('parcels.geojson', driver='GeoJSON')` | Handles CRS reprojection, property type coercion, feature collection wrapping. |

**Key insight:** Every component of this phase has a canonical published implementation. Build NOTHING from scratch except the orchestration glue (`scripts/run_phase2.sh`, the verifier, the multi-tag cohort assigner — which is genuinely Fair-Haven-specific).

---

## Section 8: Common Pitfalls

### Pitfall 1: Altair MaxRowsError on cohort time-series
**What goes wrong:** Saving a chart with > 5,000 rows of inline data raises `MaxRowsError`.
**Why it happens:** Vega-Lite spec embeds data inline by default; large specs bloat the JSON and slow render.
**How to avoid:** For any chart on `modiv_history.parquet` (80k rows), write the data separately and reference by URL: `alt.Chart('/src/data/timeseries_data.json').mark_line()...`. Only use inline data for ≤1,000-row aggregates.
**Warning signs:** ValueError("MaxRowsError") at chart-save time.
[CITED: altair-viz.github.io/user_guide/large_datasets.html]

### Pitfall 2: Leaflet marker icons disappear in Astro production build
**What goes wrong:** Markers render as broken-image icons on `astro build` output.
**Why it happens:** Vite tree-shakes unreferenced PNG assets. Leaflet loads icons by relative path at runtime, which Vite cannot statically detect.
**How to avoid:** Copy `marker-icon.png`, `marker-icon-2x.png`, `marker-shadow.png` from `node_modules/leaflet/dist/images/` to `viz/public/leaflet/` and set `L.Icon.Default.imagePath = '/leaflet/'` on init.
**Warning signs:** Markers visible in `npm run dev` but missing in `npm run build` preview.
[CITED: roblabs/maps-withastro README]

### Pitfall 3: HC3 robust SEs ignored at predict-time
**What goes wrong:** Practitioner reports HC3 SEs for coefficients but uses default OLS prediction intervals; reviewer points out PIs are not robust.
**Why it happens:** statsmodels' `get_prediction` uses MSE-based PI, NOT HC3-adjusted PI. There's no "robust prediction interval" in statsmodels by default.
**How to avoid:** Document this explicitly in the methodology white paper. For the parcel-level PI, the approximation is fine because the goal is point estimates for `delta_dollars`. If reviewer pushes, use bootstrap PIs (resample-with-replacement of residuals × 1000 reps).
**Warning signs:** A peer-reviewer or methodology checker asking "how are your PIs computed under HC3?".
[CITED: statsmodels.regression.linear_model.OLSResults.get_prediction docs]

### Pitfall 4: Sales-chasing test on too-few observations
**What goes wrong:** Running `detect_chasing()` on a cohort with N=8 returns spurious TRUE.
**Why it happens:** The CDF method's `cdf_gap=0.03` threshold = "3% of ratios share a value." With N=8, a single ratio at exactly 1.0 is 12.5% — instant TRUE.
**How to avoid:** The R source warns at N<30; our port preserves that warning. **Never report cohort-level CDF gap test verdicts for cohorts with N<30. Run the test only at the full-sample level (197 sales, post-ADP), not stratified.**
**Warning signs:** A cohort with `tenure_pandemic_2020_2022` showing TRUE while the overall sample shows FALSE — likely sample-size artifact.

### Pitfall 5: PROJECT.md tax rate $1.574 vs DLGS-real $1.427
**What goes wrong:** `actual_bill_i` computed with the wrong tax rate inflates by 10%.
**Why it happens:** PROJECT.md predates real-data verification; DATA-02 in REQUIREMENTS.md documents the correction.
**How to avoid:** Use the value from `src/fairhaven_tax/constants.py` (which Phase 1 wrote correctly) — DO NOT hardcode from PROJECT.md text. Add a verifier assertion: `assert abs(GENERAL_TAX_RATE_PER_100 - 1.427) < 0.01`.
**Warning signs:** Aggregate `actual_bill` summing to $43.4M instead of the published $40.34M.

### Pitfall 6: `scipy.stats.ecdf` vs the assessr R convention
**What goes wrong:** Python port returns different TRUE/FALSE than R reference on the same input.
**Why it happens:** `scipy.stats.ecdf` returns a step-function object; calling it at sample points may not match `stats::ecdf(x)(x)` in R when there are ties.
**How to avoid:** Use the explicit `np.arange(1, n+1) / n` convention shown in §4.1. Validate with the R example in the assessr docstring (`rep(1, 100)` injection should trigger TRUE).
**Warning signs:** Unit test with chased_ratios = `[normal(1, 0.15) × 900 + ones(100)]` returning FALSE.

### Pitfall 7: Forgetting to seed the `dist` method's rnorm
**What goes wrong:** Pipeline runs return TRUE one day, FALSE the next, on the same data.
**Why it happens:** R's `rnorm(n=10000)` and Python's `np.random.normal` are stochastic without a seed. Near the boundary `pct_actual ≈ pct_ideal`, this flips.
**How to avoid:** Always pass `rng = np.random.default_rng(42)` from the orchestrator (`scripts/run_phase2.sh` style) into `detect_chasing(rng=rng)`. Never call `np.random.normal` without a seeded generator.
**Warning signs:** Non-reproducible TRUE/FALSE between runs (D-67 violation).

### Pitfall 8: Reprojecting parcels at the wrong stage
**What goes wrong:** k-means clusters look like a curved smear instead of compact blobs.
**Why it happens:** Running k-means on EPSG:4326 (lat/lon degrees) — distance is non-Euclidean.
**How to avoid:** Keep `parcels.parquet` in EPSG:3424 (NJ State Plane, US ft). Reproject to 4326 ONLY when calling `to_file('parcels.geojson', driver='GeoJSON')` for Leaflet. The geopandas idiom: `gdf.to_crs(4326).to_file(...)`.
**Warning signs:** k-means silhouette score < 0.2 across all k, or visually-non-spatial clusters.

---

## Section 9: State of the Art (where to NOT diverge from convention)

| Old / wrong approach | Current best | Source |
|---|---|---|
| `cov_type='HC0'` (White 1980) | `cov_type='HC3'` (MacKinnon-White 1985) for small N | statsmodels docs; Cameron & Miller 2015 |
| Inline data in Vega-Lite | URL-referenced data for >1k rows | altair docs Large Datasets |
| Manual choropleth color | d3 diverging palette OR data-driven `style` callback in Leaflet | d3-scale-chromatic, leafletjs.com |
| Hand-written ECDF | `np.arange(1,n+1)/n` after sort (matches R `stats::ecdf` evaluated at samples) | assessr R reference |
| `client:load` for charts | `client:visible` (defer 280KB vega-embed bundle) | docs.astro.build directives reference |
| Berry's "fair share" = hedonic | Berry's "fair share" = sales-only fair-rate × sale_price | Berry 2018 CMF brief verbatim |

---

## Runtime State Inventory

> Greenfield phase (new viz scaffold + new Python modeling modules). No rename/refactor. **This section does not apply.** Plan 3 creates new directory `viz/`; it does not modify existing runtime state.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python 3.11+ | All Python modeling | ✓ | 3.14.2 (3.11 minimum per pyproject) | — |
| uv | Dependency mgmt | ✓ | 0.9.27 | — |
| statsmodels | hedonic OLS HC3 | ✓ (declared `>=0.14`) | latest 0.14.6 | — |
| scikit-learn | k-means | ✓ | 1.7.1 installed | — |
| scipy | stats.ecdf, stats.norm | ✓ | 1.15.3 installed | — |
| geopandas | GeoJSON export | ✓ | 1.1.3 latest | — |
| pyarrow | parquet I/O | ✓ (declared `>=17`) | latest 18.x | — |
| **altair** | Vega-Lite spec generation | ✗ | — | **MUST add to pyproject.toml: `altair>=5.5,<7`** |
| matplotlib | scratch EDA only | ✓ | 3.10.8 | — |
| Node.js | Astro build | ✓ | v22.12.0 | — |
| npm | Astro deps | ✓ | 11.3.0 | — |
| **Astro** | Viz framework | ✗ | — | `npm create astro@latest` in Plan 3 |
| **leaflet (npm)** | Map rendering | ✗ | — | Plan 3 installs |
| **vega-embed (npm)** | Chart rendering | ✗ | — | Plan 3 installs |
| git | Version control | ✓ | 2.50.1 | — |

**Missing dependencies with no fallback:** None — all gaps are first-time-install of declared stack components.

**Action items for Wave 0 / Plan 3:**
1. `uv add 'altair>=5.5,<7'` (Python).
2. Create `viz/` via `npm create astro@latest -- --template minimal --typescript strict` then `npm install leaflet@1.9.4 vega-embed@7.1.0 @astrojs/preact preact`.

---

## Open Questions

1. **Should Berry-faithful track and hedonic track be in separate plans or combined?**
   - What we know: D-58 lists Plan 5 as "Berry tax-shift (delta_dollars)" without specifying which definition.
   - What's unclear: whether Plan 5 ships both the sales-only Berry computation AND the hedonic-imputed full-population delta_dollars, or only the latter.
   - **Recommendation:** Plan 5 ships the **hedonic-imputed delta_dollars** for the parcel-level map (the main artifact). Add a sub-task to Plan 5 that ALSO computes and reports the Berry-faithful sales-only fair_rate × sale_price tax_shift table for the 197 sold parcels as a robustness column. The two should agree directionally on the sold sample; document any divergence.

2. **What if the hedonic R² < 0.7?**
   - What we know: REQUIREMENTS.md MODEL-02 sets R² ≥ 0.7 as the gate; literature meta-analysis (Sirmans 2008) supports this on residential.
   - What's unclear: whether 197 sales over 6 years with year FE will hit it. Pandemic price volatility may drag R² down.
   - **Recommendation:** Plan 4 must include a "robustness sub-suite" with three alternative specs: (a) headline spec from §1.5; (b) drop bedrooms (collinearity); (c) replace year_built with eff_age. Pick the spec with R² ≥ 0.7 AND lowest BIC. If NONE clears 0.7, document and proceed — the decision-gate threshold ($200K cohort shift) is robust to mild R² degradation.

3. **Does `assessr::detect_chasing` return TRUE on the assessment-year ratio (current assessment / sale price) or only the at-time-of-sale ratio (sale_assessment / sale_price)?**
   - What we know: assessr docstring says "numerator = estimated fair market value, denominator = actual sale price."
   - What's unclear: whether "estimated fair market value" means current or at-time-of-sale.
   - **Recommendation:** Use **at-time-of-sale (sale_assessment / sale_price)** per D-55 + Bloustein column. This matches the IAAO Standard's intent (the assessor's number IN PLACE when the sale happened). Run the test on current-year ratios as a robustness check only.

4. **For the Berry stratification, what are our strata?**
   - What we know: Berry uses (community_area × class × assessed_quartile × year). Fair Haven has one community.
   - What's unclear: whether `(neighborhood_FE × sale_year)` gives strata thick enough for stable weights.
   - **Recommendation:** Default to `(neighborhood_FE × sale_year)`. With 197 sales / (5-8 neighborhoods × 6 years) ≈ 4-7 sales per stratum, weights are stable. If any stratum has 0 sales, fall back to `(neighborhood_FE)` only (collapse the year dim).

5. **Do we need the Quintos KI/MKI Gini-based equity measures?**
   - What we know: assessr ships `ki()` and `mki()` per the formulas.R verbatim. PROJECT.md / REQUIREMENTS.md don't mention them.
   - What's unclear: whether the methodology white paper benefits from a third equity measure.
   - **Recommendation:** Compute and report them as a "we ran every IAAO-recognized measure" sentence in the methodology paper. Trivial code (use the R-translated version in §3 of this doc as a template). Not a Plan 6 blocker.

---

## Validation Architecture

> Phase config: `workflow.nyquist_validation: false`. **Section omitted per .planning/config.json explicit setting.**

---

## Security Domain

> Property tax data is public-record under New Jersey OPRA + DLGS publication; sale prices and assessments are public. **However, owner names trigger Daniel's Law (N.J.S.A. 47:1B-1)**.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase 2 is local-dev-only (D-64). No public auth surface. |
| V3 Session Management | no | Static-site output; no session state. |
| V4 Access Control | yes (Phase 3 hard-enforced) | Phase 2 keeps owner names ONLY in `data/processed/` and `viz/src/data/` — never in `viz/dist/` (D-65). Phase 3 will strip. |
| V5 Input Validation | yes | All data inputs are parquet from Phase 1/1.5; treat as trusted. External: SR1A, MOD-IV, Bloustein already validated. |
| V6 Cryptography | no | No secrets or PII transmission in this phase. |

### Threat patterns

| Pattern | STRIDE | Mitigation |
|---------|--------|-----------|
| Daniel's Law violation via accidental owner-name leak in `viz/dist/` | Information Disclosure | D-65 + Phase 3 strip step. Phase 2 verifier (`verify_phase2.py`) MUST assert `viz/dist/` does not exist (Phase 2 only runs `npm run dev`, never `npm run build`). |
| Accidental commit of owner names to git | Information Disclosure | `viz/src/data/overlays/*.json` MUST be `.gitignore`d in Plan 3. Only the Astro source code commits; data dumps are local-only. |
| Sales-chasing test deterministic-failure leaked as definitive | Tampering / Repudiation | Document N<30 cohorts as "underpowered, not reported"; full-sample only for headline. |
| Berry-faithful vs hedonic divergence misrepresented | Repudiation | Always report both numbers; methodology paper documents the decision rule. |

---

## Sources

### Primary (HIGH confidence — retrieved verbatim 2026-04-29)

- **Christopher Berry, "Estimating Property Tax Shifting Due to Regressive Assessments: An Analysis of Chicago, 2011 to 2015"** (Center for Municipal Finance, U Chicago Harris, Mar 15 2018) — the source of the fair_rate / fair_bill / tax_shift formulas. PDF retrieved and read pages 1-11.
  - URL: https://propertytaxproject.uchicago.edu/files/2020/02/Tax-Shifting-Due-to-Regressive-Assessments.pdf (302 → bpb-us-w2.wpmucdn.com).
- **Christopher Berry, "Reassessing the Property Tax"** (U Chicago Harris Working Paper, Feb 7 2021; SSRN 3800536) — the source of Eq. (1) `ln(A/P) ~ α_jt + β·ln(P)` regressivity-detection regression. Pages 1-15 read.
  - URL: https://propertytaxproject.uchicago.edu/files/2019/04/Berry-Reassessing-the-Property-Tax-2_7_21.pdf
- **CCAO `assessr` R package** — `R/formulas.R` (cod, prd, prb, ki, mki) and `R/sales_chasing.R` (detect_chasing, detect_chasing_cdf, detect_chasing_dist) read verbatim.
  - URLs: https://raw.githubusercontent.com/ccao-data/assessr/master/R/formulas.R ; https://raw.githubusercontent.com/ccao-data/assessr/master/R/sales_chasing.R
- **assessr documentation** — function reference + example ratio-study vignette.
  - URLs: https://ccao-data-science---modeling.gitlab.io/packages/assessr/reference/detect_chasing.html ; https://ccao-data.github.io/assessr/articles/example-ratio-study.html
- **IAAO Standard on Ratio Studies (April 2013)** — cited via assessr documentation; primary URL https://www.iaao.org/media/standards/Standard_on_Ratio_Studies.pdf

### Secondary (MEDIUM confidence — verified with official source)

- **ProPublica investigative report on Berry's $2.2B finding** (Mar 15 2018) — provides plain-English summary of the methodology that confirms the technical reading of the brief.
  - URL: https://www.propublica.org/article/cook-county-property-tax-shift-regressive-assessments
- **Vega-Altair documentation — `Chart.save()` and Large Datasets** — verified `chart.save('foo.vl.json', format='json')` produces vega-embed-compatible spec; 5000-row inline-data limit.
  - URLs: https://altair-viz.github.io/user_guide/saving_charts.html ; https://altair-viz.github.io/user_guide/large_datasets.html
- **Astro framework documentation — client directives** — verified `client:visible` semantics.
  - URL: https://docs.astro.build/en/reference/directives-reference/
- **Vega-embed README** — verified `vegaEmbed(el, spec)` API.
  - URL: https://github.com/vega/vega-embed

### Tertiary (lower confidence — pattern-only, not load-bearing)

- pascal-brand38/astro-leaflet community wrapper — confirms a community pattern exists; we recommend NOT using it (raw `<script type="module">` is simpler).
- roblabs/maps-withastro — confirms the "copy marker icons to public/" pitfall.
- Rodney Lab "Astro JS Location Map" tutorial — Svelte-based; we use raw + Preact.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Hedonic R² ≥ 0.7 is achievable on 197 sales with the recommended spec | §1.5 | Forces robustness-spec exploration; documented in Open Question #2. |
| A2 | VIF on (bedrooms, log_livable_area, bathrooms) will exceed 5; bedrooms will be droppable | §1.5 | If VIF is fine, keep bedrooms. Mild — it's a specification choice. |
| A3 | Stratification weights with `(neighborhood_FE × sale_year)` strata are stable for 197 sales | §1.4 / §2 | If thin strata appear, fall back to `(neighborhood_FE)` only — Open Question #4 covers it. |
| A4 | Class-2-only aggregate $2.74B is the correct gate (REQUIREMENTS.md DATA-01) vs $2.83B all-classes | §6.3 | Mild — affects calibration scalar by ~3%; the per-parcel ranking is unchanged. |
| A5 | The 5000-row Altair limit will only bite the cohort time-series chart, not the parcel-level chart | §5.5 | Per-parcel residual scatter at N=2,061 is fine; only the modiv_history chart needs URL-data. |
| A6 | `client:visible` is the right directive for the Chart.tsx wrapper (not `client:load`) | §5.3 | Mild perf — `client:load` works but blocks first paint. |
| A7 | `np.arange(1,n+1)/n` matches R `stats::ecdf(x)(x)` semantics for the chased-test inputs | §4.2 | Validation: unit test with `chased_ratios = [normal(1,0.15)*900 + ones(100)]` MUST return TRUE. |
| A8 | `detect_chasing_dist`'s `rnorm(n=10000)` is the only stochastic component and seeding fixes it | §4.2 | Validate by running the port twice with same seed; must produce identical results. |

**Mitigation:** Each assumption has either an early validation step (unit test) or a robustness alternative. Plan 4's hedonic spec MUST include a VIF check (A2) and Plan 7's CDF gap test MUST include the unit test from A7.

---

## Metadata

**Confidence breakdown:**
- **Berry methodology:** HIGH — primary source (2018 CMF brief) retrieved verbatim, 5-step procedure quoted directly.
- **assessr port (CDF gap test, COD/PRD/PRB):** HIGH — R source read verbatim line-by-line; direct translation.
- **IAAO formulas and thresholds:** HIGH — assessr roxygen citations verified against IAAO Standard reference URL.
- **Hedonic specification:** MEDIUM — Berry doesn't actually do this, so the spec rests on Gloudemans & Almy 2011 (cited by Berry) plus standard mass-appraisal practice. The exact feature list is a defensible default but not "the" canonical spec.
- **Astro+Leaflet+Vega-Lite stack:** MEDIUM-HIGH — Astro 6 stable, Leaflet 1.9.4 stable, vega-embed 7.1 stable. Integration patterns work; specific code in §5 has not been runtime-tested.
- **Effect-size thresholds:** MEDIUM — translated from Cook scale to Fair Haven scale by linear scaling; the $200K decision-gate from PROJECT.md is consistent.

**Research date:** 2026-04-29
**Valid until:** 2026-07-29 (3 months — Berry methodology is stable; Astro/leaflet/vega-embed minor versions may drift but the integration pattern is stable).

---

*Research conducted by gsd-phase-researcher per `/gsd-research-phase` (or integrated into `/gsd-plan-phase`). All claims tagged [VERIFIED], [CITED], or [ASSUMED] inline. Planner consumes this document verbatim when locking the hedonic spec, the fair_bill formula(s), the CDF gap test algorithm, and the Astro/Leaflet/Vega-Lite stack.*
