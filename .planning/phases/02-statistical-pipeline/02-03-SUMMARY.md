---
phase: 02-statistical-pipeline
plan: 03
subsystem: viz
tags: [astro-scaffold, leaflet, preact, drawer, parcel-detail, cohort-viz]
requires:
  - data/processed/parcels.parquet (Phase 1 ingest_njgin)
  - data/processed/prc.parquet (D-32, Phase 1.5 build_prc_parquet)
  - data/processed/sales.parquet (Phase 1 ingest_sr1a)
  - data/processed/modiv_history.parquet (D-34, Phase 1.5 build_modiv_history)
provides:
  - viz/ Astro 6.2 scaffold with @astrojs/preact
  - viz/src/components/ParcelMap.astro (Leaflet map with dual cohort+tax encoding)
  - viz/src/components/parcel/ParcelDetail.tsx + sections (Header, Identity, Building, Assessment, TaxContext, Sales, History, DataQuality)
  - viz/src/components/parcel/DrawerApp.tsx (client-side drawer island)
  - viz/src/components/TownComposition.tsx (donuts + avg-tax bars + cumulative-position chart)
  - viz/src/pages/index.astro (full-viewport map + drawer)
  - viz/src/pages/parcel/[pin].astro (standalone server-rendered parcel page)
  - viz/src/pages/town-composition.astro (cohort composition + ADP-era trajectory)
  - viz/src/data/parcels_full.json (joined per-parcel data, 25 MB / 2,061 records)
  - viz/src/data/parcels.geojson (deed-stripped polygons, Daniel's Law-safe)
  - viz/src/data/town_aggregates.json (cohort totals)
  - viz/src/data/cohort_history.json (37 years × 5 cohorts)
  - viz/src/data/overlays/renovations.json (renovation-event overlay)
  - viz/public/leaflet/ vendored marker icons
  - scripts/build_parcels_geojson.py
  - scripts/build_parcels_full_data.py (cohort tagging, unified-sales dedup, renovation join)
  - scripts/build_cohort_history.py (per-year per-cohort time series)
  - scripts/derive_renovation_events.py (5-signal triangulation)
  - Makefile targets: build-geojson, build-renovations, build-cohort-history, build-parcels-full, viz-data, viz-install, viz-dev
affects:
  - none (additive; D-65 compliance — owner names suppressed in published GeoJSON)
tech-stack:
  added:
    - astro@6.2 + @astrojs/preact
    - leaflet@1.9.4 + @types/leaflet
    - vega-embed (per-parcel charts)
  patterns:
    - Astro-processed `<script>` (NOT `<script define:vars>`) for bundler-resolved bare-specifier imports
    - DOM data-attribute passthrough (data-center, data-zoom, data-overlays) instead of inline classic-script var injection
    - import.meta.glob('/src/data/overlays/*.json', { eager: true }) for build-time overlay aggregation
    - atomic write pattern (.tmp + Path.replace) for parcels_full.json (D-63 hot-reload contract)
    - Preact components in `viz/src/components/parcel/sections/` rendered both server-side (parcel/[pin].astro) and client-side (DrawerApp)
key-files:
  created:
    - viz/astro.config.mjs (host 0.0.0.0:4322, allowedHosts for tailscale)
    - viz/src/components/ParcelMap.astro
    - viz/src/components/parcel/ParcelDetail.tsx + 8 section components
    - viz/src/components/parcel/parcel.css (design tokens)
    - viz/src/components/TownComposition.tsx
    - viz/src/pages/index.astro
    - viz/src/pages/parcel/[pin].astro
    - viz/src/pages/town-composition.astro
    - scripts/build_parcels_geojson.py
    - scripts/build_parcels_full_data.py
    - scripts/build_cohort_history.py
    - scripts/derive_renovation_events.py
status: complete
notes: |
  This SUMMARY is retroactive — the work was completed and committed across many
  iterative sessions in late April 2026, but the SUMMARY.md was never written at
  the time. Recording it here so wave 1 closes cleanly before wave 2 (hedonic).

  The implementation goes well beyond the original Plan 03 scope: it includes
  the cohort-tagging schema (no_deed_since_1989, tenure_pre_2015, tenure_2015_2019,
  tenure_pandemic_2020_2022, tenure_post_pandemic_2023plus), the dual cohort+tax
  map encoding, full per-parcel drawer with renovation badge, the standalone
  /town-composition page with cumulative-undertaxation view, and the renovation-
  event derivation pipeline. All artifacts reproducible from
  data/processed/* via `make viz-data`.

  H1 directional signal already visible in raw cohort aggregates before any
  hedonic modeling: pre-2015 (50.6% of parcels, 46.1% of levy) vs pandemic+
  (27.8% of parcels, 31.0% of levy). ADP-era cumulative position by cohort:
  no_deed_since_1989 -$5.43M, tenure_post_pandemic_2023plus +$5.18M.
---

# 02-03 — Astro Visualization Scaffold (retrospective)

## What was built

A complete Astro 6.2 + Preact + Leaflet visualization layer under `viz/`,
serving as the runtime container for every Phase-2 chart, overlay, and map.

The scaffold ships:

1. **A full-viewport Leaflet map** (`/`) with dual encoding — fill = tenure
   cohort, outline = last-year tax magnitude. Click a parcel → opens a
   right-side drawer rendering the full per-parcel detail tree.

2. **A standalone per-parcel page** (`/parcel/[pin]`) statically generated
   for all 2,061 parcels at build time, sharing the same `ParcelDetail`
   component tree as the drawer.

3. **A town-composition page** (`/town-composition`) showing cohort donuts,
   avg-tax-per-parcel bars, pre/post-2015 + pre/post-pandemic split blocks
   with a "skew" column, and the ADP-era cumulative-position chart.

4. **A central data joiner** (`scripts/build_parcels_full_data.py`) that
   merges parcels.parquet + prc.parquet + sales.parquet + modiv_history.parquet
   + the data-quality and renovation overlays into a single per-parcel record.

## Why this is wave-1 / pre-modeling

Plans 04 (hedonic), 05 (Berry shift), 06 (ratio study), and 07 (CDF gap)
all need a place to publish their Vega-Lite charts and per-parcel overlays
without re-deriving the parcel join. This scaffold is that place. Charts
land in `viz/src/data/charts/`, per-parcel overlays in
`viz/src/data/overlays/`, and pages in `viz/src/pages/`.

## Verification

- `cd viz && npx astro build` builds 2,063 pages cleanly (1 index + 1 town
  composition + 2,061 per-parcel pages).
- `make viz-data` regenerates all derived JSON from `data/processed/*` with
  no manual steps.
- Daniel's Law (D-65): the published GeoJSON contains no owner names —
  `scripts/build_parcels_geojson.py` strips them at build time.
