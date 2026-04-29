# Phase 1: Data Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-29
**Phase:** 01-data-foundation
**Areas discussed:** Storage + layout, Data versioning, Validation policy, CRS + SR1A parsing

---

## Storage + Project Layout

### Q: Storage backend for parcel + sales tables

| Option | Description | Selected |
|--------|-------------|----------|
| Parquet + GeoParquet | File-based, geopandas-native, perfect for ~2,200 parcels | ✓ |
| SQLite + SpatiaLite | Single-file DB with SQL/spatial via SpatiaLite | |
| PostGIS | Full Postgres + spatial; overkill for v1 | |

**User's choice:** Parquet + GeoParquet
**Notes:** Aligns with reproducibility goal for public methodology artifact.

### Q: Python project tooling

| Option | Description | Selected |
|--------|-------------|----------|
| uv + pyproject.toml | Modern, fast, lockfile-based | ✓ |
| Poetry | Mature, slower than uv | |
| pip + requirements.txt + venv | Lowest barrier, but not 2025-2026 best practice | |

**User's choice:** uv + pyproject.toml

### Q: Project layout

| Option | Description | Selected |
|--------|-------------|----------|
| src/fairhaven_tax/ package + scripts/ + notebooks/ | Importable package with notebooks for exploration | (rejected — notebooks excluded) |
| Flat scripts + notebooks only | Faster start, harder to test | (rejected — notebooks excluded) |

**User's choice (free-text):** No notebooks under any circumstances. Streamlit (or current best-practice quick-viz Python tool) for interactive visualization. Scripts produce graphs; consume in serving state.
**Notes:** Strong directive captured as feedback memory at `~/.claude/projects/-Users-paul-coding-fairhaven-tax-assessment/memory/feedback_no_notebooks.md`. Layout resolved as `src/fairhaven_tax/` package + `scripts/` + Streamlit app — no notebooks. Overrides REQUIREMENTS.md OUT-05's mention of Jupyter/Quarto.

---

## Data Versioning

### Q: Raw download layout

| Option | Description | Selected |
|--------|-------------|----------|
| data/raw/{source}/{YYYY-MM-DD}/ + manifest.json | Per-source dated snapshots with provenance | ✓ |
| data/raw/{source}/latest/ only | Overwrite on each download | |
| git-lfs tracked snapshots | Tightest reproducibility but storage cost | |

**User's choice:** Dated snapshots + manifest.json

### Q: Processed artifacts location

| Option | Description | Selected |
|--------|-------------|----------|
| data/processed/ separate, .gitignored | Strict raw/processed split, rebuildable | ✓ |
| data/processed/ committed to git | Reviewable but bloats repo | |

**User's choice:** Separate + gitignored

### Q: Source pinning depth

| Option | Description | Selected |
|--------|-------------|----------|
| URL + sha256 + retrieved-at in manifest | Full provenance, anti-tamper | ✓ |
| URL only | Lighter; trusts upstream | |

**User's choice:** Full pin

---

## Validation Policy

### Q: Behavior on out-of-tolerance validation

| Option | Description | Selected |
|--------|-------------|----------|
| Hard-fail with diagnostic report | Pipeline exits non-zero, writes _VALIDATION-FAILED.md | ✓ |
| Warn + continue | Logs deviations but proceeds | |
| Interactive prompt | Friction in batch runs | |

**User's choice:** Hard-fail
**Notes:** Critical for defensible public methodology.

### Q: Tolerance threshold

| Option | Description | Selected |
|--------|-------------|----------|
| ±5% per REQUIREMENTS | As written | ✓ |
| ±2% (tighter) | Stricter | |
| Two-tier: warn ±2%, fail ±5% | Hybrid | |

**User's choice:** ±5%

### Q: NU code rejection handling

| Option | Description | Selected |
|--------|-------------|----------|
| Reject + log to rejections.parquet with reason | Audit trail | ✓ |
| Reject silently | Lighter logs | |
| Include if unknown | Risks contaminating hedonic | |

**User's choice:** Reject + log

---

## CRS + SR1A Parsing

### Q: Geometry CRS handling

| Option | Description | Selected |
|--------|-------------|----------|
| Native EPSG:3424, reproject to 4326 only on export | Accurate spatial ops, single reprojection | ✓ |
| Reproject to 4326 at ingest | Simpler but breaks distance/area accuracy | |
| Store both, flag-controlled | Maximum flex, more code | |

**User's choice:** Native EPSG:3424

### Q: SR1A schema strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Tolerant column-mapper per year + rejection log | Resilient to format drift | ✓ |
| Strict pydantic schema per year | Catches drift loudly but blocks pipeline | |
| One unified loose schema | Lightest but risks silent collisions | |

**User's choice:** Tolerant per-year mapper

### Q: Same-parcel sale dedupe for last arms-length

| Option | Description | Selected |
|--------|-------------|----------|
| Latest sale_date, tie-break by highest price | Standard ratio-study practice | ✓ |
| Latest sale_date, tie-break by deed_ref order | Deterministic but ignores price | |
| Keep all, decide downstream | Pushes inconsistency to Phase 2 | |

**User's choice:** Latest date, tie-break by highest price

---

## Claude's Discretion

- CLI framework choice (typer/click/argparse)
- Makefile vs justfile
- Logging library (structlog vs stdlib)
- Test framework (assumed pytest)
- Internal helper module naming
- pyarrow vs geopandas.to_parquet choice for non-geo tables

## Deferred Ideas

- PostGIS migration if multi-town comparison strains parquet
- git-lfs raw data tracking if external audit demands bit-for-bit reproducibility
- OPRS scraping for multi-sale histories (v2 EXT-01)
- NJACTB / Rutgers Bloustein historical MOD-IV (v2 longitudinal)
- NU code expansion (NU=8, 27, 28) if hedonic training set is too thin in Phase 2
- OPRA to NJ Treasury for unredacted SR1A detail (v2 yellow tier)
