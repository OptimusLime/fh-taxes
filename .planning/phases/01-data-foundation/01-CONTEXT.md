# Phase 1: Data Foundation - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Acquire three green-tier datasets (NJGIN Monmouth Parcels+MOD-IV file geodatabase, NJ DLGS Property Tax Tables, NJ DOT SR1A annual sales 2018-2025), reconcile and validate against published Fair Haven figures, and persist a queryable parcel universe + sales table keyed by PAMS_PIN. Filtered to MUN_CODE=1314, class 2 residential. No scraping, no OPRA, no v2 datasets in this phase. Output: validated parquet/GeoParquet artifacts and a constants module exposing the 2025/2026 tax rate breakdown and total levy.

</domain>

<decisions>
## Implementation Decisions

### Storage & Project Layout

- **D-01 (Storage):** Parquet + GeoParquet for both raw-derived and processed tables. No SQLite, no PostGIS in v1. Geopandas-native; zero database setup; reproducible for public methodology artifact.
- **D-02 (Tooling):** `uv` + `pyproject.toml` (no pip+requirements, no poetry). Aligns with 2025-2026 Python best practice; fast lockfile-based.
- **D-03 (Project layout):** `src/fairhaven_tax/` importable package with submodules (`ingest/`, `validate/`, `persist/`, plus future `model/`, `calc/`, `output/` for Phase 2/3). `scripts/` directory for thin CLI entry-points that compose package functions. Streamlit app (later phases) lives at `src/fairhaven_tax/app/` or `apps/`. **NO Jupyter/Quarto notebooks anywhere in the project — categorically excluded per user directive.** Scripts produce static figures (PNG/SVG/HTML); interactive viz uses Streamlit. This overrides REQUIREMENTS.md OUT-05's mention of "Jupyter or Quarto notebook" — substitute "make/shell script + Streamlit dashboard" before planning.
- **D-04 (Entry point):** `Makefile` (or `justfile`) with targets `make ingest`, `make validate`, `make all` orchestrating the pipeline end-to-end from raw downloads to processed parquet.

### Data Versioning

- **D-05 (Raw layout):** `data/raw/{source}/{YYYY-MM-DD}/` — per-source dated snapshots. Sources: `njgin_monmouth_parcels`, `dlgs_tax_tables`, `sr1a`. Each snapshot directory contains the original archive(s) plus a `manifest.json`.
- **D-06 (Manifest schema):** `manifest.json` per snapshot records `source_url`, `retrieved_at` (ISO-8601 UTC), `sha256` per downloaded file, `bytes`, optional `etag`/`last_modified` from upstream, plus any year coverage notes (e.g., SR1A `coverage_years: [2018,...,2025]`).
- **D-07 (Processed location):** `data/processed/` strictly separate from `data/raw/`. Contains derived parquet/GeoParquet (parcels, sales, rejections, validation_report). `data/processed/` is `.gitignored` — rebuildable from raw via pipeline. Never edited by hand.
- **D-08 (Git tracking):** `data/raw/` committed via git-lfs IS NOT chosen — too heavy for v1. Raw lives locally; manifests are the reproducibility contract. If a collaborator needs to reproduce, the manifest's URL + sha256 lets them re-fetch and verify. Reconsider in v2 if the artifact needs full bit-for-bit reproducibility for an external auditor.

### Validation Policy

- **D-09 (Failure mode):** Hard-fail on out-of-tolerance. Pipeline exits non-zero; writes `data/processed/_VALIDATION-FAILED.md` with delta breakdown by property class and tax map area. No silent continuation. This is critical for a methodology artifact that will be defended publicly.
- **D-10 (Tolerance):** ±5% per REQUIREMENTS DATA-01 — covers rounding in published Director's Ratio + minor MOD-IV revisions between annual cycles. Single threshold (not two-tier). If tightening becomes useful in Phase 2 calibration, revisit then.
- **D-11 (Validation targets):** (a) parcel count ~2,200 ±5% after class-2 filter; (b) aggregate assessed value ~$2.77B ±5%; (c) Sum of SR1A 2018-2025 arms-length sales ≥ 200 (sanity floor for hedonic training set). Each target produces a line in `data/processed/validation_report.parquet`.
- **D-12 (NU code rejection):** Only NU codes ∈ {0, 7, 10, 26, 33} retained as arms-length. All other SR1A rows persisted to `data/processed/rejections.parquet` with columns: `parcel_pin`, `sale_date`, `sale_price`, `nu_code`, `deed_ref`, `rejection_reason`, `source_file`. Audit trail is non-negotiable.

### CRS & Geometry

- **D-13 (Native CRS):** Store geometries in EPSG:3424 (NAD83 / New Jersey State Plane, US survey feet) — the native NJGIN distribution CRS. All spatial joins, k-means centroid computation (Phase 2), and distance/area operations happen in projected coordinates for accuracy.
- **D-14 (Export CRS):** Reproject to EPSG:4326 (WGS84) only at GeoJSON export time (Phase 3). Single reprojection step; Leaflet is happy with WGS84.
- **D-15 (CRS validation):** Pipeline asserts every input shapefile/FGDB is EPSG:3424; any deviation triggers hard-fail (NJGIN has been stable on this).

### SR1A Parsing

- **D-16 (Schema strategy):** Tolerant column-mapper config per year. `src/fairhaven_tax/ingest/sr1a/columns/{YYYY}.yaml` maps actual file columns to canonical schema. Unrecognized rows or unmappable columns → `rejections.parquet` with reason. Resilient to NJ Treasury format drift.
- **D-17 (Canonical sales schema):** `parcel_pin` (PAMS_PIN), `sale_date` (date), `sale_price` (decimal), `nu_code` (string), `deed_book`, `deed_page`, `grantor_redacted` (bool), `source_file`, `source_year`.
- **D-18 (Dedupe / last-sale resolution):** For each parcel, "last arms-length sale" = MAX(sale_date) over arms-length rows; tie-break by MAX(sale_price) on same date (handles same-day correction deeds). The full multi-sale history is retained in `sales.parquet`; the resolved last-sale columns are denormalized onto `parcels.parquet` for fast cohort tagging in Phase 2.

### MOD-IV ↔ SR1A Reconciliation

- **D-19 (Cross-check):** For each parcel, compare MOD-IV's last-sale-date/price field against the SR1A-derived last arms-length sale. Discrepancies (date >180 days off OR price >5% off) logged to `reconciliation_diffs.parquet` with both source values. This is descriptive — does not block — but Phase 2 modeling uses SR1A-derived values as ground truth (SR1A is what NJ Treasury uses for the Director's Ratio).

### Claude's Discretion

- Naming of internal Python module helpers, choice of CLI framework (typer vs click vs argparse — pick one and stay consistent), exact Makefile/justfile target names, `.gitignore` contents beyond data/processed/, test framework (pytest assumed), logging library (structlog or stdlib).
- Whether to use `pyarrow` directly vs going through `geopandas.to_parquet` for non-geo tables (probably mix: `pyarrow` for sales/rejections/validation_report, `geopandas` for parcels).
- Specific sha256 / manifest implementation details.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context (in-repo)
- `.planning/PROJECT.md` — full project context, ADP background, legal framing
- `.planning/REQUIREMENTS.md` — REQ-IDs DATA-01..04, STORE-01..02 covered by this phase; **note: OUT-05 mentions Jupyter/Quarto — must be substituted with scripts + Streamlit per D-03 before Phase 3 planning**
- `.planning/ROADMAP.md` — phase structure and success criteria
- `~/.claude/projects/-Users-paul-coding-fairhaven-tax-assessment/memory/feedback_no_notebooks.md` — categorical rejection of notebooks (applies to all phases)

### External (web; no local copies yet)
- NJGIN Open Data Hub, Monmouth County Parcels + MOD-IV — `njogis-newjersey.opendata.arcgis.com` (search "Monmouth Parcels"). Native EPSG:3424. ~75 MOD-IV fields joined to parcel polygons. OWNER_NAME redacted statewide (Daniel's Law).
- NJ DLGS Property Tax Tables — `nj.gov/dca/dlgs/resources/Property_Tax_info.shtml` — Excel files with annual `YYtaxes.xls` URL pattern; contains per-municipality levy-by-purpose breakdown.
- NJ DOT SR1A Sales File — `nj.gov/treasury/taxation/lpt/statdata.shtml` — annual deed-level statewide bulk file with NU codes. Redacted (no grantor/grantee names) post-Daniel's Law.
- IAAO Standard on Ratio Studies (April 2013) — informs NU code interpretation. Codes 0/7/10/26/33 = arms-length per NJ DOT documentation.
- `johnjreiser/NJParcelTools` (GitHub) — reference Python+PostgreSQL ingestion scripts for NJGIN MOD-IV/parcel files. Reuse / adapt rather than reinvent. (License: check before vendoring.)
- N.J.S.A. 47:1B-1 et seq. (Daniel's Law) — owner names not present in NJGIN distribution; no Phase 1 redaction work needed, but ingest must NOT join any external owner data.

### Schema specs (to be created during Phase 1 implementation)
- `docs/schemas/parcels.md` — canonical parcel schema (to be authored)
- `docs/schemas/sales.md` — canonical sales schema (to be authored)
- `docs/schemas/rejections.md` — rejection-log schema (to be authored)
- `docs/manifests/manifest_schema.md` — `manifest.json` schema (to be authored)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- None — greenfield repo. No existing Python package, no prior pipelines, no codebase map.
- Reference implementation available: `johnjreiser/NJParcelTools` for NJGIN MOD-IV ingestion patterns (cite/adapt, do not vendor wholesale until license checked).

### Established Patterns

- None — this phase establishes the patterns. Decisions D-01 through D-19 ARE the patterns the rest of the project will follow.

### Integration Points

- Phase 2 consumes `data/processed/parcels.parquet` (with denormalized last_sale_date / last_sale_price / last_sale_nu_code columns) for cohort tagging and as the prediction target for the hedonic model.
- Phase 2 consumes `data/processed/sales.parquet` (filtered to 2023-2025 arms-length) as the hedonic training set.
- Phase 2 consumes constants module `src/fairhaven_tax/constants.py` (or similar) exposing `TAX_RATE_PER_HUNDRED = Decimal("1.574")`, the six-component breakdown, and `TOTAL_LEVY` extracted from DLGS in DATA-02.
- Phase 3 consumes `data/processed/parcels.parquet` (with geometry) for GeoJSON export — reprojects EPSG:3424 → EPSG:4326 at that boundary.

</code_context>

<specifics>
## Specific Ideas

- The user views notebooks as anti-pattern. Apply across the entire project; do not let downstream agents reintroduce them via templates. (Captured in memory at `~/.claude/projects/-Users-paul-coding-fairhaven-tax-assessment/memory/feedback_no_notebooks.md`.)
- Streamlit is the preferred quick-viz tool. Static figures from scripts for the public artifact; Streamlit for the investigator's local exploration UI.
- Reproducibility lever is the `manifest.json` (URL + sha256 + retrieved-at) per raw snapshot, NOT git-lfs in v1.

</specifics>

<deferred>
## Deferred Ideas

- **PostGIS migration** — if multi-town comparison or the Rumson placebo (v2 REG-04) becomes a real workload, parquet may strain. Reconsider then.
- **git-lfs raw data tracking** — defer until external audit/reviewer demands bit-for-bit reproducibility.
- **OPRS scraping for multi-sale histories per parcel** — v2 (EXT-01). Not in Phase 1 scope.
- **NJACTB or Rutgers Bloustein historical MOD-IV (1989-present)** — v2 if longitudinal assessment trends become relevant.
- **NU code expansion (e.g., NU=8, 27, 28)** — currently rejected. Defer reconsideration to Phase 2 if hedonic training set is too thin.
- **OPRA to NJ Treasury for unredacted SR1A grantor/grantee detail** — v2 yellow-tier expansion; not needed for parcel-level Berry analysis.

### Reviewed Todos (not folded)

(None — no pending todos surfaced for this phase.)

</deferred>

---

*Phase: 01-data-foundation*
*Context gathered: 2026-04-29*
