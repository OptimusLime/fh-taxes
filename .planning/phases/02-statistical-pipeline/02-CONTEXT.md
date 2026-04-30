# Phase 2: Statistical Pipeline - Context

**Created:** 2026-04-30
**Status:** Ready for research + planning
**Trigger:** Phase 1.5 complete — `prc.parquet` (2,060 × 57), `modiv_history.parquet` (80,329 × 18), and `sales.parquet` (197 enriched arms-length sales) are on disk. Phase 2 turns these into per-parcel `delta_dollars`, IAAO COD/PRD by tenure cohort, and a TRUE/FALSE CDF gap test verdict — replicating the Cook County / U Chicago Center for Municipal Finance methodology as the published reference.

<domain>
## Phase Boundary

Build a reproducible Python pipeline that:
1. **Validates** the Phase 1 + Phase 1.5 data inputs before any modeling
2. **Visualizes** every intermediate and final output via an Astro.js dev-mode static site (Leaflet parcel maps + Altair/Vega-Lite town-level charts)
3. **Replicates Christopher Berry's Cook County hedonic + tax-shift methodology** as the first-pass reference
4. **Produces** per-parcel `delta_dollars`, cohort COD/PRD ratio-study tables, and a Python port of `assessr::detect_chasing()` with TRUE/FALSE verdict
5. **Persists** all artifacts to `data/processed/*.parquet` + `viz/src/data/*.{json,geojson,vl.json}`

**In scope:**
- Data validation gate over `prc.parquet`, `sales.parquet`, `parcels.parquet`, `modiv_history.parquet`
- Berry/Cook County methodology research (hedonic spec, fair-bill formula, output artifacts)
- `assessr::detect_chasing()` Python port (CDF gap test for sales chasing per IAAO Standard on Ratio Studies)
- Hedonic OLS on 2020-2025 arms-length sales (197 obs) with year FE + k-means neighborhood FE (k ∈ {5..8}), HC3 robust SEs
- Per-parcel Berry tax-shift `delta_dollars = actual_bill − fair_bill` for all 2,060 class-2 parcels
- Multi-tag tenure cohort assignment + IAAO ratio study (COD ≤15%, PRD 0.98-1.03)
- Astro.js static site under `viz/` with Leaflet parcel map + per-page Altair charts + hot-reload via JSON file-watch
- Single `make` target (or shell script) reproducing the entire pipeline end-to-end

**Out of scope (deferred to v2 / Phase 3 / later):**
- Pre-ADP modeling (1989-2013) — different mass-appraisal regime, deferred unless post-ADP results raise specific questions
- Tax-appeal cohort analysis — Tier-C OPRS endpoint, deferred per `.planning/deferred/oprs-tier-c.md`
- Public-facing publication — Phase 3 owns Daniel's Law Redactor registration, aggregation decisions, owner-name suppression, and external deployment
- Deed text mining / grantor-grantee network analysis
- Causal inference / counterfactual analysis ("what tax bill would the 2020 buyer have paid if assessed identically to the 2003 buyer next door") — Phase 2 stays descriptive
</domain>

<decisions>
## Implementation Decisions

### Guiding lights (north stars)

- **D-50 — Replicate Cook County / Berry first-pass approach.** Christopher Berry's published Cook County methodology (U Chicago Center for Municipal Finance) is the reference template. Our hedonic spec, fair-bill formula, output artifacts, and visualization patterns must match Berry's first published approach. Diverge only with documented justification. *Why:* Berry's work was peer-reviewed, validated publicly, and produced the headline $1.7B / $2.2B Cook County tax-shift figures. Replicating it (a) gives us a public anchor, (b) lets us debug by comparing to known outputs, (c) protects against methodology drift.

- **D-51 — Statistical-power preference over tight-spec preference.** Where a tradeoff exists between fewer-but-cleaner observations and more-but-noisier, take more. Default scope is post-ADP regime (~2014-2025). Expand backward only if post-ADP results raise specific gaps. *Why:* 197 arms-length sales 2020-2025 vs 92 sales 2023-2025 — the broader window with year FE gives ~2× the obs:param ratio for stable HC3 inference.

- **D-52 — Yearly correctness within regime.** Each year's parcel "true value" estimate must be informed by that year's sales/comps (or near-year with documented rough correlation). No leaking 2024 sales into 2018 valuations. *Why:* The mass-appraisal model under ADP is supposed to track each year's market; testing it requires the same temporal hygiene the assessor's model claims to have.

### Cohort design (multi-tag, NOT exclusive buckets)

- **D-53 — Multi-tag tenure cohorts.** Each parcel carries an unordered set of tags from these orthogonal axes:
  - **Tenure-window tags** (mutually exclusive within the axis):
    - `tenure_pre_2015` — last arms-length sale before 2015-01-01
    - `tenure_2015_2019` — sale 2015-2019 (post-ADP, pre-pandemic)
    - `tenure_pandemic_2020_2022` — sale 2020-2022 (COVID money-supply era)
    - `tenure_post_pandemic_2023plus` — sale 2023+ (sustained inflation / millennial-demand era)
  - **Special tags** (orthogonal, can co-occur with any tenure tag):
    - `never_sold` — no arms-length sale since 1989 in `modiv_history`. Implies `tenure_pre_2015` by construction. **Predicted "worst offender" cohort if H1/H2 true** — explicitly preserved as its own tag for the analysis.
    - `family_sale_only` — only NU≠blank/00 transfers since 1989 (Van Decker / Daniel's Law warning cohort)

  *Why multi-tag:* "never_sold" is the most interesting subset of pre_2015 (long-tenured). Collapsing it into a single bucket loses the signal. Multi-tag also lets the COD/PRD report compute statistics per tag axis separately.

### Data scope (regimes + windows)

- **D-54 — Hedonic training window: 2020-2025 (197 arms-length sales) with year FE.** Within post-ADP regime. Year FE absorbs pandemic vs post-pandemic price-level differences. *Why D-51:* 92 sales 2023-2025 has obs:param ≈ 7:1; 197 with year FE has obs:param ≈ 12:1 — clears the 10:1 minimum for stable HC3 inference.

- **D-55 — CDF gap test scope: post-ADP (2014-2025) first pass.** Use Bloustein `modiv_history.parquet` `sale_assessment` column for the canonical "assessment at time of sale" — gives ~700-900 (parcel × sale_year) ratio data points in the post-ADP window. Pre-ADP 1989-2013 is deferred (different regime). *Why:* The IAAO sales-chasing test requires assessment-at-time-of-sale, which Bloustein freezes correctly. We have orders of magnitude more data than the original research plan assumed.

- **D-56 — Berry "fair_bill" formula: DEFERRED to research.** The researcher (gsd-phase-researcher in the plan-phase workflow) must investigate Berry's published Cook County methodology and recommend the exact formula. Locked options to evaluate:
  - (a) Pure hedonic-predict: `fair_bill_i = (predicted_value_i / Σ predicted_value) × total_levy`
  - (b) Hybrid: hedonic-predict for parcels with comparables, current-assessment fallback otherwise
  - (c) Berry's actual published formula (TBD via research)

  The planner picks up the recommendation in PLAN.md. Default-of-last-resort is (a).

### Plan structure (dependency-ordered, every plan ships viz)

- **D-57 — Plans are dependency-ordered; each plan delivers a 100% working artifact + visualization.** No half-finished handoffs. A plan is not done until: code is committed, tests pass, parquet/JSON artifacts are written, AND the Astro viz scaffold has been updated with the corresponding map overlay or chart page.

- **D-58 — Plan list (locked outline; planner refines task-level breakdown):**
  1. **Data validation gate** — range/null/cross-source checks on prc/sales/modiv_history. Emits `data/processed/validation_report.parquet` + Altair quality-dashboard charts + map overlay flagging parcels with data issues. **Blocks every downstream plan.**
  2. **Cook/Berry research deliverable** — researcher pulls Berry's exact hedonic spec + fair_bill formula + assessr::detect_chasing internals + IAAO Standard on Ratio Studies + relevant Cook County technical docs. Output is a research doc (`02-RESEARCH.md`) the modeling plans cite verbatim.
  3. **Astro.js visualization scaffold** — `viz/` directory with Astro skeleton, base parcel map (Leaflet + GeoJSON of all 2,061 parcels), parcel-detail popup component reading per-parcel JSON, JSON-data file-watch hot reload. **Becomes the spot-check tool every subsequent plan must update.**
  4. **Hedonic OLS + true value estimation** — replicate Berry's spec from research output. Emits fitted model, per-parcel `estimated_true_value`, residual diagnostics, Altair coefficient/residual charts, choropleth overlay of estimated_true_value.
  5. **Berry tax-shift (delta_dollars)** — formula sourced from research. Emits per-parcel `delta_dollars` + diverging-color choropleth overlay + Altair distribution chart.
  6. **IAAO ratio study by cohort** — COD/PRD per cohort tag. Emits cohort summary table + Altair box-plot/strip-plot pages.
  7. **CDF gap test (assessr Python port)** — TRUE/FALSE verdict + the canonical CDF-with-cliff plot (the single most persuasive artifact from the research plan).
  8. **Integration + reproducibility** — single `make` or shell-script target, all artifacts persisted, `viz/` fully populated, `verify_phase.py` smoke-test exits 0 if all artifacts exist with expected schemas.

  **Wave map (planner finalizes):**
  - Wave 1 (parallel): Plan 1 + Plan 2
  - Wave 2: Plan 3 (depends on Plan 1's validated data)
  - Wave 3: Plan 4 (depends on Plans 1, 2, 3)
  - Wave 4 (parallel): Plans 5, 6, 7 (all depend on Plan 4's true_value estimates)
  - Wave 5: Plan 8

### Visualization stack (locked)

- **D-59 — Astro.js as the visualization framework.** Static-first, hot-reload via JSON-data file-watch, deployable as static site. Lives under `viz/` (new top-level dir). Phase 3 inherits this scaffold and adds redaction + publication layers. *Why Astro:* (a) static output makes Phase 3 deployable, (b) hot-reload supports iterative dev, (c) component model fits map + charts cleanly, (d) overlap with Phase 3's Leaflet map artifact eliminates rework.

- **D-60 — Map layer: Leaflet rendering parcel GeoJSON + per-parcel JSON overlays.**
  - Base: `viz/src/data/parcels.geojson` (one Feature per parcel, properties = stable identity columns)
  - Per-model overlays: `viz/src/data/overlays/<model_name>.json` keyed by PAMS_PIN (e.g. `delta_dollars.json`, `assessment_ratio.json`, `tenure_cohort.json`)
  - User clicks a parcel → popup reads ALL overlays for that pin and shows them
  - Color-coded heatmaps for each numeric overlay (diverging palette centered at zero for delta_dollars; sequential for ratios)

- **D-61 — Chart layer: Altair (Python) → Vega-Lite JSON → Astro pages via vega-embed.**
  - Each modeling plan saves charts as `viz/src/data/charts/<name>.vl.json` via `altair.Chart.save("...", format="json")`
  - Astro page imports the JSON and renders with `vega-embed`
  - Page-per-analysis: `/hedonic`, `/tax-shift`, `/ratio-study`, `/cdf-gap-test`, `/data-quality`, etc.

- **D-62 — Every plan ships visualizations.** No exceptions. The data-validation plan ships a "data quality dashboard". The hedonic plan ships coefficient tables AND residual scatter AND choropleth of predicted values. The CDF gap test ships the cliff-detection plot. **A plan that lacks a visualization update is not done.**

- **D-63 — Hot-reload trigger contract.** Modeling code writes to `viz/src/data/*.{json,geojson,vl.json}` via atomic .tmp+rename. Astro dev server's file-watcher detects the rename and reloads the affected page. Operator workflow: run `npm run dev` in `viz/`, run any `scripts/build_*.py` in another terminal, see results live.

### Privacy & compliance

- **D-64 — Owner names: Phase 2 internal-only.** Owner names MAY appear in Astro popups during local dev (we already extract them from m4.html and Bloustein). The Astro app is treated as a private staging environment in Phase 2. **Phase 3 owns the publication decision** — whether to publish parcel-level (with Daniel's Law Redactor registration + owner suppression) or aggregate-only (block-group choropleth). CONTEXT.md does NOT pre-commit to which.

- **D-65 — Daniel's Law footprint isolation.** All owner-name fields stay in `data/processed/*.parquet` and the `viz/src/data/*.json` (local-only). Nothing under `viz/dist/` (a hypothetical public build) ever contains owner names — Phase 3 build pipeline strips them at static-build time.

### Sales-chasing test (D-55 detail)

- **D-66 — `assessr::detect_chasing()` Python port — exact statistical test deferred to research.** The R reference implementation (CCAO open-source assessr package) uses a specific test on the empirical CDF of sale ratios near 1.0. The researcher must extract the exact algorithm. Default-of-last-resort: Mann-Whitney U on ratios in (0.95, 1.05) vs the rest, with the cliff signature being a sharp density spike just above 1.0.

### Reproducibility

- **D-67 — Single-command pipeline.** `make all` (or `bash scripts/run_phase2.sh`) runs every step from raw inputs to all artifacts and viz JSON. Fixed random seeds for k-means and any sampling. Pinned Python deps in `pyproject.toml`. Astro deps in `viz/package.json` with lockfile.

- **D-68 — verify_phase.py smoke gate.** A `scripts/verify_phase2.py` script reads each expected output (parquet schemas, JSON keys, viz file existence) and exits 0/1. Wired into the integration plan (Plan 8) and into `gsd-verifier` for the phase-completion gate.

</decisions>

<canonical_refs>
## Canonical References

### In-repo
- `.planning/PROJECT.md` — project context, hypotheses H1/H2/H3
- `.planning/REQUIREMENTS.md` — MODEL-01..03, CALC-01..03, TEST-01 (this phase)
- `.planning/ROADMAP.md` — Phase 2 success criteria (5)
- `.planning/phases/01.5-oprs-collection/01.5-CONTEXT.md` — D-32 prc.parquet schema, D-34 modiv_history schema
- `data/processed/prc.parquet` — 2,060 × 57 hedonic features (output of Phase 1.5 Plan 5)
- `data/processed/sales.parquet` — 197 enriched arms-length sales (output of Phase 1.5 Plan 5)
- `data/processed/parcels.parquet` — 2,061 NJGIN parcels with geometry (Phase 1)
- `data/processed/modiv_history.parquet` — 80,329 (parcel × year) Bloustein historical (Phase 1.5 Plan 6)
- `src/fairhaven_tax/persist/parquet_io.py` — atomic parquet write helper
- `src/fairhaven_tax/constants.py` — MUN codes, NU code sets, expected counts, tax rate

### External (researcher must investigate before planning)

**Cook County / Berry methodology — TOP PRIORITY for D-50/D-55/D-66:**
- Christopher Berry's publications via U Chicago Center for Municipal Finance (`https://harris.uchicago.edu/centers-institutes/center-municipal-finance`)
- Cook County Assessor's Office (CCAO) `assessr` R package source (`https://github.com/ccao-data/assessr`) — `detect_chasing()` implementation in particular
- "Reassessing the Property Tax" (Berry, U Chicago Harris Working Paper 2021)
- The headline Cook County tax-shift report (the $2.2B residential figure)

**IAAO standards:**
- IAAO Standard on Ratio Studies (April 2013) — formal sales-chasing definition + COD/PRD formulas
- Indiana 50 IAC 27-2-11 — regulatory definition of sales chasing

**Statistical / model references:**
- statsmodels OLS with `cov_type='HC3'` for robust SEs
- scikit-learn `KMeans` for neighborhood clustering (k ∈ {5..8})
- Altair → Vega-Lite spec format (`https://altair-viz.github.io`)
- Astro framework + `vega-embed` for chart rendering

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable assets

- **`prc.parquet` schema (D-32 from Phase 1.5):** 57 columns including `bedrooms`, `bathrooms`, `room_count`, `kitchens`, `livable_area`, `eff_age`, `condition`, `quality_grade`, `foundation`, `exterior`, `roof_type`, `roof_material`, `heating_type`, `ac_type`, `fireplaces`, `garage_type`, `sewer`, `water`, plus year_built, lot dims, current assessment. **99%+ feature coverage** for the hedonic.

- **`modiv_history.parquet` schema (D-34):** 80,329 rows, one per (parcel × year), 1989-2025. **`sale_assessment` column is the gold-standard CDF gap test input** — it's the assessor's number AT TIME OF SALE, frozen forever. ~25,598 (parcel × sale_year) rows have both `sale_assessment` and `sale_price` populated.

- **`sales.parquet` (197 sales)** is enriched with `family_sale_flag`, `nu_code`, `grantor`, `grantee` from sr.cgi via Phase 1.5 Plan 5.

- **`parcels.parquet`** has GeoPandas geometries in EPSG:3424 (NJ State Plane US ft). Reproject to EPSG:4326 only at the GeoJSON-export boundary (Leaflet is WGS84).

- **`scripts/ingest_sr1a.py` template** (refuse-zero-rows + atomic parquet write + POSIX exit codes) is the pattern for Plan 8's verifier and for any plan that emits a parquet artifact.

- **Atomic write helper:** `src/fairhaven_tax/persist/parquet_io.py` already provides `.tmp+rename`.

### Patterns to follow

- **Modeling code structure:** `src/fairhaven_tax/models/<name>.py` for analysis modules (hedonic, berry_shift, ratio_study, cdf_gap_test). One pure-function entry point per module that takes parquet paths and returns DataFrames + Altair Chart objects. Cross-module orchestration happens in `scripts/run_phase2.py`.

- **Test fixture pattern:** mirror `tests/test_oprs_parse_*.py` — small synthetic-but-realistic input fixtures, deterministic seeded model fits, snapshot the output schema and a few key statistics.

- **Viz data flow:**
  - Modeling script computes results → DataFrame
  - DataFrame is split into (a) full per-parcel JSON dump → `viz/src/data/overlays/<name>.json`, (b) Altair chart → `viz/src/data/charts/<name>.vl.json`
  - Astro page imports both, renders map + chart side-by-side

### Integration points

- Phase 3 will inherit the entire `viz/` scaffold and:
  - Strip owner names at static-build time
  - Add Daniel's Law Redactor registration banner + privacy notice
  - Decide aggregation level (parcel vs block-group) per a then-current legal review
  - Add a methodology-white-paper page at `viz/src/pages/methodology.astro`

</code_context>

<deferred>
## Deferred Ideas

- **Pre-ADP modeling (1989-2013).** Different mass-appraisal regime. Would need a regime-change indicator dummy in any pooled model. Defer until post-ADP results raise specific questions about long-horizon trends.
- **Causal / counterfactual analysis.** "What would the 2020 buyer pay if assessed identically to the 2003 buyer next door?" Phase 2 stays descriptive; counterfactual machinery is v2.
- **Tax-appeal cohort analysis.** Tier-C OPRS endpoint, deferred per `.planning/deferred/oprs-tier-c.md`.
- **Deed-level grantor-grantee network analysis.** "Did long-tenured owners successfully fight their assessment more often than recent buyers?" Requires Tier-C tax-appeal data.
- **Spatial autocorrelation diagnostics (Moran's I, LISA).** PySAL deferred to v2 per CLAUDE.md.
- **Public publication.** Phase 3 territory.
- **Aggregate-only viz mode.** Block-group choropleth alternative if Phase 3 legal review rules out parcel-level. Defer the decision; Phase 2 builds the parcel-level version with the option to aggregate later.

</deferred>

---

*Phase: 02-statistical-pipeline*
*Context gathered: 2026-04-30 via /gsd-discuss-phase*
