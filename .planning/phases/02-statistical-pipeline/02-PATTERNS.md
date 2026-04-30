# Phase 2: Statistical Pipeline - Pattern Map

**Mapped:** 2026-04-29
**Files analyzed:** ~35 new files across 7 code-bearing plans (Plan 2 is research-only)
**Analogs found:** 28 / 35 with strong in-repo analogs; 7 are NEW patterns (Astro/Leaflet/Altair) flagged below

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| **Plan 1 — Validation** | | | | |
| `src/fairhaven_tax/validation/__init__.py` | package-init | n/a | `src/fairhaven_tax/validate/__init__.py` | exact |
| `src/fairhaven_tax/validation/checks.py` | validation | batch transform | `src/fairhaven_tax/validate/gates.py` | exact |
| `scripts/run_validation.py` | CLI driver | request-response (file→file) | `scripts/validate_phase1.py` | exact |
| `data/processed/validation_report.parquet` | artifact | output | `data/processed/validation_report.parquet` (Phase 1) | exact (already exists; will be extended schema) |
| `viz/src/data/charts/data_quality.vl.json` | viz artifact | Altair → Vega-Lite JSON | NONE (new pattern) | NEW |
| `viz/src/data/overlays/data_quality.json` | viz overlay | per-PIN JSON | NONE (new pattern) | NEW |
| `tests/test_validation.py` | test | fixture-driven | `tests/test_validate_gates.py` | exact |
| **Plan 3 — Astro scaffold** | | | | |
| `viz/astro.config.mjs` | config | n/a | NONE | NEW (Astro docs) |
| `viz/package.json` | config | n/a | NONE | NEW |
| `viz/src/pages/index.astro` | route/page | static render | NONE | NEW |
| `viz/src/pages/parcel/[pin].astro` | route/page (dynamic) | static render | NONE | NEW |
| `viz/src/components/ParcelMap.astro` | component | client-side render | NONE | NEW (Leaflet) |
| `viz/src/components/VegaChart.astro` | component | client-side render | NONE | NEW (vega-embed) |
| `viz/src/data/parcels.geojson` | data artifact | output | (none — first GeoJSON in repo) | NEW |
| `scripts/build_parcels_geojson.py` | CLI driver | parquet → GeoJSON | `scripts/ingest_njgin.py` (CRS reproject sections) + `scripts/build_modiv_history.py` (script template) | strong role-match |
| **Plan 4 — Hedonic** | | | | |
| `src/fairhaven_tax/models/__init__.py` | package-init | n/a | `src/fairhaven_tax/validate/__init__.py` | exact |
| `src/fairhaven_tax/models/hedonic.py` | model/service | batch transform | `src/fairhaven_tax/validate/gates.py` (pure-fn shape) + `src/fairhaven_tax/ingest/sr1a/parse.py` (Decimal/None hygiene) | role-match |
| `scripts/run_hedonic.py` | CLI driver | parquet → parquet+JSON | `scripts/build_modiv_history.py` | exact |
| `data/processed/hedonic_fit.parquet` | artifact | output | `data/processed/modiv_history.parquet` | exact |
| `viz/src/data/overlays/estimated_true_value.json` | viz overlay | per-PIN JSON | NONE | NEW |
| `viz/src/data/charts/hedonic_residuals.vl.json` | viz artifact | Altair JSON | NONE | NEW |
| `viz/src/data/charts/hedonic_coefficients.vl.json` | viz artifact | Altair JSON | NONE | NEW |
| `tests/test_hedonic.py` | test | seeded synthetic | `tests/test_validate_gates.py` (synthetic builders) + `tests/test_oprs_parse_sr.py` (synthetic-fixture pattern) | strong role-match |
| **Plan 5 — Berry tax-shift** | | | | |
| `src/fairhaven_tax/models/berry_shift.py` | model/service | batch transform | `src/fairhaven_tax/validate/reconcile.py` + `src/fairhaven_tax/validate/gates.py` | role-match |
| `scripts/run_berry_shift.py` | CLI driver | parquet → parquet+JSON | `scripts/build_modiv_history.py` | exact |
| `data/processed/delta_dollars.parquet` | artifact | output | `data/processed/prc.parquet` | exact |
| `viz/src/data/overlays/delta_dollars.json` | viz overlay | per-PIN JSON | NONE | NEW |
| `viz/src/data/charts/delta_distribution.vl.json` | viz artifact | Altair JSON | NONE | NEW |
| `tests/test_berry_shift.py` | test | seeded synthetic | `tests/test_validate_gates.py` | role-match |
| **Plan 6 — Ratio study** | | | | |
| `src/fairhaven_tax/models/ratio_study.py` | model/service | batch transform | `src/fairhaven_tax/validate/gates.py` | role-match |
| `scripts/run_ratio_study.py` | CLI driver | parquet → parquet+JSON | `scripts/build_modiv_history.py` | exact |
| `data/processed/cohort_ratio_study.parquet` | artifact | output | `data/processed/validation_report.parquet` (long format) | exact |
| `viz/src/data/charts/cohort_cod_prd.vl.json` | viz artifact | Altair JSON | NONE | NEW |
| `tests/test_ratio_study.py` | test | seeded synthetic | `tests/test_validate_gates.py` | role-match |
| **Plan 7 — CDF gap test** | | | | |
| `src/fairhaven_tax/models/cdf_gap_test.py` | model/service | batch transform + statistic | `src/fairhaven_tax/validate/gates.py` | role-match |
| `scripts/run_cdf_gap_test.py` | CLI driver | parquet → JSON+vl.json | `scripts/validate_phase1.py` (boolean verdict + exit code) + `scripts/build_modiv_history.py` | strong role-match |
| `data/processed/cdf_gap_test_result.json` | artifact | output (small JSON not parquet) | NONE in-repo (every other artifact is parquet) | partial — use atomic-write pattern |
| `viz/src/data/charts/cdf_gap_test.vl.json` | viz artifact | Altair JSON | NONE | NEW |
| `tests/test_cdf_gap_test.py` | test | seeded synthetic | `tests/test_validate_gates.py` | role-match |
| **Plan 8 — Integration** | | | | |
| `scripts/run_phase2.sh` | CLI driver | shell orchestration | `Makefile` (target chaining) | role-match |
| `scripts/verify_phase2.py` | CLI driver | smoke test | `scripts/validate_phase1.py` | exact |
| `Makefile` (modified) | config | n/a | `Makefile` (existing) | exact (extend) |

---

## Pattern Assignments

### `src/fairhaven_tax/validation/checks.py` (Plan 1, validation/batch-transform)

**Analog:** `src/fairhaven_tax/validate/gates.py`

**Note on naming:** Phase 1 uses singular `validate/` (verb). The CONTEXT plan list uses `validation/` (noun). Either works; recommend **renaming new module to `validate/checks.py` and adding to existing package** to avoid two parallel validation packages. (Flag this for planner; planner makes the call.)

**Imports + dataclass-result pattern** (`src/fairhaven_tax/validate/gates.py:1-33`):
```python
from __future__ import annotations
from dataclasses import dataclass, asdict
from decimal import Decimal
from pathlib import Path

import geopandas as gpd
import pandas as pd

from fairhaven_tax import constants
from fairhaven_tax.persist.parquet_io import write_parquet, ensure_processed_dir


class ValidationFailure(Exception):
    """Raised when one or more validation gates fail."""


@dataclass
class GateResult:
    name: str
    expected: Decimal | int
    actual: Decimal | int
    tolerance: Decimal | None
    passed: bool
    message: str
```

**Gate function pattern** (`gates.py:42-59`):
```python
def validate_parcel_count(parcels_gdf: gpd.GeoDataFrame) -> GateResult:
    """D-11(a): |actual - 2200| / 2200 ≤ 5%."""
    actual = int(len(parcels_gdf))
    expected = constants.EXPECTED_PARCEL_COUNT
    tol = constants.VALIDATION_TOLERANCE
    pct = _pct_diff(Decimal(actual), Decimal(expected))
    passed = pct <= tol
    return GateResult(
        name="parcel_count",
        expected=expected, actual=actual, tolerance=tol, passed=passed,
        message=f"parcel count {actual} vs expected {expected} (pct_diff={pct:.4f}, tolerance={tol})",
    )
```

**run_all aggregator + report writer** (`gates.py:104-129`):
```python
def run_all_gates(parcels_gdf, sales_df, processed_dir=None) -> tuple[bool, list[GateResult]]:
    results = [validate_parcel_count(parcels_gdf), validate_aggregate_assessed(parcels_gdf), ...]
    proc = ensure_processed_dir(processed_dir)
    rows = [{"gate_name": r.name, "expected": str(r.expected), "actual": str(r.actual),
             "tolerance": str(r.tolerance) if r.tolerance is not None else None,
             "passed": r.passed, "message": r.message} for r in results]
    df = pd.DataFrame(rows)
    write_parquet(df, proc / "validation_report.parquet")
    return all(r.passed for r in results), results
```

**Phase 2 extension:** add range/null cross-source checks (e.g., `prc.livable_area` populated, `modiv_history.sale_assessment` non-null where `sale_price` populated). Each check returns a `GateResult`; aggregator extends the existing `validation_report.parquet` schema (add a `source` column distinguishing Phase 1 vs Phase 2 gates).

---

### `scripts/run_validation.py` (Plan 1, CLI driver)

**Analog:** `scripts/validate_phase1.py`

**Header + path constants** (`validate_phase1.py:1-18`):
```python
#!/usr/bin/env python
"""Phase 1 validation gate (D-09).

Loads data/processed/{parcels,sales}.parquet, runs all validation gates,
writes _VALIDATION-FAILED.md and exits non-zero on out-of-tolerance.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from fairhaven_tax.persist.parquet_io import read_geoparquet, read_parquet
from fairhaven_tax.validate.gates import run_all_gates

PROCESSED = Path("data/processed")
FAIL_FILE = PROCESSED / "_VALIDATION-FAILED.md"
```

**Main + exit-code pattern** (`validate_phase1.py:52-84`):
```python
def main() -> int:
    parcels_path = PROCESSED / "parcels.parquet"
    sales_path = PROCESSED / "sales.parquet"
    if not parcels_path.exists() or not sales_path.exists():
        print(f"ERROR: missing {parcels_path} or {sales_path}; run `make ingest` first.",
              file=sys.stderr)
        return 1

    parcels = read_geoparquet(parcels_path)
    sales = read_parquet(sales_path)
    ok, results = run_all_gates(parcels, sales)

    if not ok:
        _write_failure_doc(results)
        print("VALIDATION FAILED — see data/processed/_VALIDATION-FAILED.md", file=sys.stderr)
        sys.exit(1)
    if FAIL_FILE.exists():
        FAIL_FILE.unlink()
    print("Validation PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**POSIX exit codes used in repo:** `0` = success, `1` = expected failure (gate failed), `2` = preflight failure (missing input file). Plan 1 must follow.

---

### `scripts/build_parcels_geojson.py` (Plan 3, parquet → GeoJSON)

**Analog:** `scripts/ingest_njgin.py` (for the EPSG:3424 → 4326 reproject) + `scripts/build_modiv_history.py` (for the script skeleton).

**Script skeleton** (`scripts/build_modiv_history.py:1-63`):
```python
#!/usr/bin/env python
"""Build viz/src/data/parcels.geojson from data/processed/parcels.parquet (D-60)."""
from __future__ import annotations
import sys
from pathlib import Path

from fairhaven_tax.persist.parquet_io import read_geoparquet

BASE = Path("data/processed/parcels.parquet")
OUT = Path("viz/src/data/parcels.geojson")


def main() -> int:
    if not BASE.exists():
        print(f"ERROR: missing {BASE}; run `make ingest-njgin` first", file=sys.stderr)
        return 2

    gdf = read_geoparquet(BASE)
    if len(gdf) == 0:
        print("ERROR: zero parcels — refusing to declare success", file=sys.stderr)
        return 2

    # Reproject 3424 (NJ State Plane US ft) → 4326 (WGS84) for Leaflet.
    gdf_wgs = gdf.to_crs(constants.CRS_EXPORT)  # CRS_EXPORT = "EPSG:4326"

    # Atomic write: .tmp → rename
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".geojson.tmp")
    gdf_wgs.to_file(tmp, driver="GeoJSON")
    tmp.rename(OUT)
    print(f"Wrote {len(gdf_wgs)} features → {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**CRS reproject reference:** `src/fairhaven_tax/constants.py:40-41`:
```python
CRS_NATIVE: str = "EPSG:3424"   # NAD83 / New Jersey State Plane US ft (NJGIN distribution)
CRS_EXPORT: str = "EPSG:4326"   # WGS84 — Phase 3 GeoJSON export only
```

**Phase 2 note (Daniel's Law / D-64):** This GeoJSON's `properties` MUST NOT include owner names. Restrict to stable identity columns (pams_pin, block, lot, mun, prop_loc). Owner mailing addresses go in per-pin overlay JSONs (local-only), never in `parcels.geojson`.

---

### `viz/astro.config.mjs`, `viz/package.json`, `viz/src/components/*.astro` (Plan 3, NEW PATTERN)

**No in-repo analog.** Astro + Leaflet + vega-embed is greenfield. Cite external docs and locked decisions:

- D-59: Astro.js as the visualization framework
- D-60: Leaflet for parcel map; per-PIN overlay JSON keyed by PAMS_PIN
- D-61: Altair → Vega-Lite JSON → vega-embed
- D-63: Hot-reload contract = atomic .tmp+rename writes to `viz/src/data/`

**Suggested `viz/package.json` deps** (planner finalizes versions):
```json
{
  "name": "fairhaven-tax-viz",
  "type": "module",
  "scripts": { "dev": "astro dev", "build": "astro build" },
  "dependencies": {
    "astro": "^4.0",
    "leaflet": "^1.9",
    "vega": "^5",
    "vega-lite": "^5",
    "vega-embed": "^6"
  }
}
```

**Astro page → JSON-data-import contract (D-63 hot reload):**
- Astro `getStaticPaths()` reads `viz/src/data/parcels.geojson` to enumerate `/parcel/[pin]` routes
- Each page imports per-overlay JSONs via `import overlay from '../data/overlays/delta_dollars.json'`
- Modeling scripts atomic-write to those exact paths (.tmp + rename); Astro dev server reloads

**Leaflet + Astro integration reference (external):** Astro docs "Client-side scripts" (https://docs.astro.build/en/guides/client-side-scripts/), Leaflet quickstart (https://leafletjs.com/examples/quick-start/). Mount Leaflet in `<script>` block of `ParcelMap.astro` with `client:load` — Astro's island hydration pattern.

---

### `src/fairhaven_tax/models/hedonic.py` (Plan 4, model/batch-transform)

**Analog:** `src/fairhaven_tax/validate/gates.py` (pure-function shape, dataclass result, processed-dir parameterization for testability)

**Module shape — pure-function, takes parquet paths, returns DataFrame + dataclass result:**
```python
"""Hedonic OLS on 2020-2025 arms-length sales (D-54).

Spec sourced from 02-RESEARCH.md (Berry/Cook County replication).
Year FE + k-means neighborhood FE (k ∈ {5..8}), HC3 robust SEs.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.cluster import KMeans

from fairhaven_tax import constants
from fairhaven_tax.persist.parquet_io import read_parquet, write_parquet


@dataclass
class HedonicFit:
    coefficients: pd.DataFrame
    residuals: pd.DataFrame
    per_parcel_predictions: pd.DataFrame  # PAMS_PIN, estimated_true_value
    r_squared: float
    n_obs: int


def fit_hedonic(
    sales_path: Path,
    prc_path: Path,
    *,
    seed: int = 42,
    k_neighborhood: int = 6,
) -> HedonicFit:
    """Fit Berry-style hedonic; return dataclass with all artifacts.

    Pure function. Caller handles parquet/JSON write + chart export.
    """
    ...


def predict_true_value(fit: HedonicFit, prc_df: pd.DataFrame) -> pd.DataFrame:
    """Apply fitted model to all 2,060 class-2 parcels. Returns
    (pams_pin, estimated_true_value, residual)."""
    ...


def coefficient_chart(fit: HedonicFit) -> alt.Chart:
    """Altair coefficient + 95% CI plot. Saved by caller via .save(path, format='json')."""
    ...


def residual_chart(fit: HedonicFit) -> alt.Chart:
    """Altair predicted-vs-actual residual scatter."""
    ...
```

**Decimal/None hygiene reference** (`src/fairhaven_tax/ingest/sr1a/parse.py:74-83` — the `_parse_int_money` helper showing how the codebase handles missing numeric values from Decimal-preserving parquet). Hedonic must coerce Decimals → float at the statsmodels boundary, then back to Decimal for the output parquet.

**Seed contract (D-67):** all stochastic ops (`KMeans`, any bootstrap) take `random_state=seed` with `seed=42` default.

---

### `scripts/run_hedonic.py` (Plan 4, CLI driver)

**Analog:** `scripts/build_modiv_history.py`

**Full pattern with refuse-zero-rows guard + atomic write + Altair save** (synthesized from `build_modiv_history.py` + research):
```python
#!/usr/bin/env python
"""Run hedonic OLS → hedonic_fit.parquet + per-parcel overlay + Altair charts.

Exit codes:
  0 — success
  2 — missing input parquet OR zero rows fit
"""
from __future__ import annotations
import sys
from pathlib import Path

from fairhaven_tax.models.hedonic import (
    coefficient_chart, fit_hedonic, predict_true_value, residual_chart,
)
from fairhaven_tax.persist.parquet_io import read_parquet, write_parquet

SALES = Path("data/processed/sales.parquet")
PRC = Path("data/processed/prc.parquet")
OUT_PARQUET = Path("data/processed/hedonic_fit.parquet")
OUT_OVERLAY = Path("viz/src/data/overlays/estimated_true_value.json")
OUT_RESID_CHART = Path("viz/src/data/charts/hedonic_residuals.vl.json")
OUT_COEF_CHART = Path("viz/src/data/charts/hedonic_coefficients.vl.json")


def _atomic_write_json(path: Path, payload) -> None:
    """Atomic .tmp+rename for JSON (D-63 hot-reload contract)."""
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, default=str, indent=2))
    tmp.rename(path)


def main() -> int:
    if not SALES.exists() or not PRC.exists():
        print(f"ERROR: missing {SALES} or {PRC}; run Phase 1.5 first", file=sys.stderr)
        return 2

    fit = fit_hedonic(SALES, PRC)
    if fit.n_obs == 0:
        print("ERROR: zero observations after filter — refusing to declare success",
              file=sys.stderr)
        return 2

    prc_df = read_parquet(PRC)
    preds = predict_true_value(fit, prc_df)
    write_parquet(preds, str(OUT_PARQUET))

    # Per-parcel overlay: keyed by pams_pin (D-60)
    overlay = {row["pams_pin"]: {"estimated_true_value": str(row["estimated_true_value"]),
                                  "residual": str(row.get("residual"))}
               for _, row in preds.iterrows()}
    _atomic_write_json(OUT_OVERLAY, overlay)

    # Altair → Vega-Lite JSON via .save() (D-61)
    coefficient_chart(fit).save(str(OUT_COEF_CHART), format="json")
    residual_chart(fit).save(str(OUT_RESID_CHART), format="json")

    print(f"Wrote {len(preds)} predictions, R²={fit.r_squared:.4f}, n={fit.n_obs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Altair `.save(..., format='json')` is a NEW pattern in the repo.** Reference: https://altair-viz.github.io/user_guide/saving_charts.html#json-format. Saves the Vega-Lite spec without rendered HTML. This is what `viz/src/components/VegaChart.astro` consumes via `vega-embed`.

---

### `src/fairhaven_tax/models/berry_shift.py` (Plan 5, Berry tax-shift)

**Analog:** Same pure-function shape as `hedonic.py`. Dollar-delta computation is a deterministic transform; no stochastic component.

**Formula source:** `02-RESEARCH.md` (TBD-by-researcher per D-56). Default-of-last-resort:
```python
def compute_delta_dollars(
    estimated_true_value: pd.DataFrame,  # pams_pin, estimated_true_value
    actual_assessment: pd.DataFrame,     # pams_pin, current_year_assessment
    total_levy: Decimal = constants.TOTAL_LEVY,
) -> pd.DataFrame:
    """Berry tax-shift per D-56 option (a) — pure hedonic-predict.

    fair_share_i = predicted_value_i / Σ predicted_value
    fair_bill_i  = fair_share_i × total_levy
    actual_bill_i = (actual_assessment_i / 100) × tax_rate_per_hundred
    delta_dollars_i = actual_bill_i − fair_bill_i

    Returns: pams_pin, fair_bill, actual_bill, delta_dollars
    """
```

**TOTAL_LEVY constant already populated** — see `constants.py:54`: `TOTAL_LEVY = Decimal("40339309.769999996")`.

---

### `src/fairhaven_tax/models/ratio_study.py` (Plan 6, IAAO COD/PRD)

**Analog:** `src/fairhaven_tax/validate/gates.py` for the result-aggregation shape; `src/fairhaven_tax/validate/reconcile.py` for cross-source merging.

**Cohort-tag pattern from CONTEXT D-53** — multi-tag (set membership), NOT exclusive bucket:
```python
def assign_cohort_tags(modiv_history: pd.DataFrame) -> pd.DataFrame:
    """Returns pams_pin → set[str] of cohort tags per D-53.

    Tenure-window tags (mutually exclusive within axis):
      tenure_pre_2015, tenure_2015_2019,
      tenure_pandemic_2020_2022, tenure_post_pandemic_2023plus
    Special tags (orthogonal, can co-occur):
      never_sold, family_sale_only
    """


def cod_prd_by_tag(ratios: pd.DataFrame, tags: pd.DataFrame) -> pd.DataFrame:
    """Compute COD ≤15%, PRD 0.98-1.03 per IAAO Standard, per cohort tag.

    Returns long-format: cohort_tag, n, median_ratio, cod, prd, cod_pass, prd_pass.
    """
```

**Output parquet shape mirrors `validation_report.parquet` (long format):** one row per (tag, statistic) with pass/fail boolean.

---

### `src/fairhaven_tax/models/cdf_gap_test.py` (Plan 7, assessr port)

**Analog:** `src/fairhaven_tax/validate/gates.py` for the boolean-verdict pattern; `src/fairhaven_tax/ingest/bloustein.py` for the `sale_assessment` column source.

**`assessr::detect_chasing()` exact algorithm comes from `02-RESEARCH.md`.** Default-of-last-resort per D-66: Mann-Whitney U on sale ratios in (0.95, 1.05) vs the rest.

**Sale-ratio data source (D-55):** `data/processed/modiv_history.parquet` rows where `sale_assessment` AND `sale_price` are both non-null (~25,598 rows; ~700-900 in 2014-2025 post-ADP window).

**Result artifact = JSON, not parquet** (small; one verdict + statistic + n). Use atomic-write helper:
```python
def _atomic_write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, default=str, indent=2))
    tmp.rename(path)
```

**The cliff-detection plot is the headline visualization** (per D-58 plan 7). Altair: empirical CDF of ratios with vertical line at 1.0 + shaded gap region.

---

### `tests/test_hedonic.py`, `tests/test_berry_shift.py`, etc. (synthetic-fixture pattern)

**Analog:** `tests/test_validate_gates.py` (synthetic GeoDataFrame builder); `tests/test_oprs_parse_sr.py` (synthetic-but-realistic HTML fixture); `tests/test_build_prc_parquet.py` (helper-import pattern for scripts).

**Synthetic-frame builder pattern** (`tests/test_validate_gates.py:19-27`):
```python
def _parcels(n: int, value_each: Decimal | None = None) -> gpd.GeoDataFrame:
    """Build n synthetic parcels. Default value yields EXPECTED_AGGREGATE_ASSESSED."""
    if value_each is None:
        value_each = constants.EXPECTED_AGGREGATE_ASSESSED / Decimal(constants.EXPECTED_PARCEL_COUNT)
    df = pd.DataFrame({
        "pams_pin": [f"1314_{i}_1" for i in range(n)],
        "assessed_value": [value_each] * n,
    })
    return gpd.GeoDataFrame(df, geometry=[Point(0, 0)] * n, crs="EPSG:3424")
```

**Importing-script-helpers pattern** (`tests/test_build_prc_parquet.py:24-29`):
```python
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import build_prc_parquet  # noqa: E402
```

**Subprocess + exit-code test pattern** (`tests/test_validate_gates.py:82-119`) for verifying CLI driver scripts hard-fail with non-zero exit:
```python
import subprocess, sys, os
rc = subprocess.call(
    [sys.executable, str(script)],
    cwd=tmp_path,
    env={"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(repo_root / "src")},
)
assert rc != 0, "must exit non-zero on bad input"
```

**For models with stochastic components (hedonic k-means):** seed in test = `42`. Snapshot the resulting cluster centroids + first-row coefficient to detect drift.

---

### `scripts/verify_phase2.py` (Plan 8, smoke gate)

**Analog:** `scripts/validate_phase1.py` — same exit-code semantics, gate-list shape.

**What to verify (D-68):**
1. Each expected parquet file exists
2. Each parquet has expected columns (schema check via pyarrow)
3. Each `viz/src/data/charts/*.vl.json` parses as valid JSON with `"$schema"` Vega-Lite key
4. `viz/src/data/parcels.geojson` parses as valid GeoJSON FeatureCollection
5. `data/processed/cdf_gap_test_result.json` has keys `{verdict, statistic, n}`
6. Per-PIN overlay JSONs are non-empty dicts

Exit 0 = all checks pass; exit 1 = one or more failed; exit 2 = preflight (input dirs missing).

**Reuse pattern from gate aggregator:** return `list[GateResult]` from individual checks; aggregate.

---

### `scripts/run_phase2.sh` (Plan 8, orchestrator)

**Analog:** `Makefile` chain `acquire → ingest → reconcile → validate` (lines 26-54).

**Recommendation:** prefer extending `Makefile` over a bash script (operator already runs `make`). Add Phase 2 targets:
```makefile
.PHONY: validate-phase2 build-geojson run-hedonic run-berry-shift run-ratio-study run-cdf-gap-test verify-phase2 phase2

validate-phase2:
	$(PYTHON) scripts/run_validation.py

build-geojson:
	$(PYTHON) scripts/build_parcels_geojson.py

run-hedonic:
	$(PYTHON) scripts/run_hedonic.py

run-berry-shift: run-hedonic
	$(PYTHON) scripts/run_berry_shift.py

run-ratio-study: run-hedonic
	$(PYTHON) scripts/run_ratio_study.py

run-cdf-gap-test:
	$(PYTHON) scripts/run_cdf_gap_test.py

verify-phase2:
	$(PYTHON) scripts/verify_phase2.py

phase2: validate-phase2 build-geojson run-hedonic run-berry-shift run-ratio-study run-cdf-gap-test verify-phase2
```

If `run_phase2.sh` is required as well (D-67 mentions both), it's a thin wrapper: `set -euo pipefail; make phase2`.

---

## Shared Patterns

### Pattern S1 — Atomic write (.tmp + rename)

**Source:** Already used in `src/fairhaven_tax/persist/parquet_io.py` (parquet via pyarrow handles atomicity internally) + `datasets/collect_oprs.py:28` ("components write to .tmp sibling, rename on success").

**Apply to:** ALL JSON / GeoJSON / Vega-Lite JSON writes in `viz/src/data/` per D-63 hot-reload contract. Parquet writes go through `write_parquet()` which is already safe.

**Canonical helper** (add to a new `src/fairhaven_tax/persist/json_io.py` or inline in scripts):
```python
def atomic_write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, default=str, indent=2))
    tmp.rename(path)
```

**Note for Astro hot-reload (D-63):** Astro's file watcher needs to see a complete-file rename event, not in-place writes. `.tmp + rename` is exactly right.

---

### Pattern S2 — Refuse zero rows ("refusing to declare success")

**Source:** `scripts/build_modiv_history.py:49-52`, `scripts/ingest_sr1a.py:41-44`, `scripts/build_prc_parquet.py:195-198`.

**Apply to:** EVERY new `scripts/run_*.py` and `scripts/build_*.py`. Never write an empty parquet.

```python
if len(df) == 0:
    print("ERROR: zero rows — refusing to declare success", file=sys.stderr)
    return 2
```

---

### Pattern S3 — POSIX exit codes

**Source:** Repo convention across all scripts. `0` = success; `1` = expected failure (gate failed, validation out of tolerance); `2` = preflight (missing input files / cache / snapshot). See `scripts/build_prc_parquet.py:14-16` for explicit doc.

**Apply to:** every CLI script in Plan 1, 3, 4, 5, 6, 7, 8.

---

### Pattern S4 — `_latest_snapshot()` helper

**Source:** `scripts/build_modiv_history.py:27-37`, `scripts/ingest_sr1a.py:13-20`, `scripts/ingest_njgin.py:70-77`. Used when reading dated raw snapshots.

**Apply to:** Phase 2 doesn't read raw snapshots (it reads `data/processed/*.parquet`), so this pattern is mostly NOT applicable. Exception: if any plan reads a dated DLGS or NJGIN refresh, follow this helper.

---

### Pattern S5 — Decimal hygiene at parquet boundaries

**Source:** `src/fairhaven_tax/persist/parquet_io.py:30` ("Decimals preserved as object dtype"); `src/fairhaven_tax/ingest/sr1a/parse.py:74-83` (Decimal coercion); `scripts/ingest_njgin.py:29-38` (`_to_decimal` helper).

**Apply to:** Plan 4, 5 (hedonic + Berry shift) where dollar values flow through statsmodels (which wants float). Cast Decimal → float at model fit; cast back to Decimal when writing parquet.

```python
def _to_float(d):  # at model-fit boundary
    return float(d) if d is not None else np.nan

def _to_decimal(f):  # at parquet-write boundary
    return Decimal(str(round(f, 2))) if not np.isnan(f) else None
```

---

### Pattern S6 — Pure-function modeling, side-effects in scripts

**Source:** Implicit across `src/fairhaven_tax/validate/gates.py` (pure aggregator), `src/fairhaven_tax/ingest/sr1a/parse.py` (returns `(df, df)` tuple), with side effects (parquet writes, exit codes) confined to `scripts/`.

**Apply to:** Plan 4, 5, 6, 7. `src/fairhaven_tax/models/<name>.py` exposes pure functions returning DataFrames + Altair Chart objects. `scripts/run_<name>.py` orchestrates: read parquet → call pure fns → write parquet + JSON + chart files.

---

### Pattern S7 — Daniel's Law footprint isolation (D-64, D-65)

**Source:** `src/fairhaven_tax/ingest/bloustein.py:8-16` (deviation note documenting that Bloustein has owner mailing addresses, not names).

**Apply to:**
- `viz/src/data/parcels.geojson` properties: NEVER include `owner_mailing_address` (D-65)
- Per-PIN overlays under `viz/src/data/overlays/`: MAY include addresses for local dev (D-64), Phase 3 strips at build
- `data/processed/*.parquet`: addresses retained internally
- New code touching owner data MUST add a 2-line note like bloustein.py's, citing D-64/D-65.

---

### Pattern S8 — Constants-driven thresholds

**Source:** `src/fairhaven_tax/constants.py` — all thresholds (parcel count, aggregate, levy, tax rate, NU codes, CRS) are module constants, never magic numbers.

**Apply to:** Plan 6 (IAAO thresholds COD ≤ 15%, PRD 0.98-1.03), Plan 7 (CDF gap test critical values), Plan 4 (k_neighborhood range). Add to `constants.py`:
```python
# IAAO Standard on Ratio Studies (April 2013) — Plan 6
IAAO_COD_RESIDENTIAL_MAX: Decimal = Decimal("15.0")  # percent
IAAO_PRD_MIN: Decimal = Decimal("0.98")
IAAO_PRD_MAX: Decimal = Decimal("1.03")

# Hedonic spec (D-54) — Plan 4
HEDONIC_TRAIN_YEAR_MIN: int = 2020
HEDONIC_TRAIN_YEAR_MAX: int = 2025
HEDONIC_K_NEIGHBORHOOD_DEFAULT: int = 6  # within {5..8}
RANDOM_SEED: int = 42  # D-67 reproducibility
```

---

## NEW Patterns (no in-repo analog — flagged for planner)

### NP1 — Altair → Vega-Lite JSON save

**Why new:** Repo has zero existing Altair usage.
**Reference:** https://altair-viz.github.io/user_guide/saving_charts.html#json-format
**Signature:** `chart.save(path, format="json")` — emits Vega-Lite spec consumable by vega-embed.
**Add dep:** `altair>=5.0` to `pyproject.toml`.

### NP2 — Astro page + island hydration for Leaflet

**Why new:** No frontend code in repo.
**References:**
- Astro: https://docs.astro.build/
- Leaflet quickstart: https://leafletjs.com/examples/quick-start/
- Astro client directives (`client:load`, `client:visible`): https://docs.astro.build/en/reference/directives-reference/#client-directives
**Pattern:** Mount Leaflet inside `<script>` block of `ParcelMap.astro` with appropriate client directive; pass GeoJSON + overlay JSON via Astro's `Astro.props` or top-level imports.

### NP3 — vega-embed in Astro component

**Why new:** No charting in repo.
**Reference:** https://github.com/vega/vega-embed
**Pattern:** `VegaChart.astro` accepts a `spec` prop (JSON path or object), client-side `vegaEmbed(container, spec)`.

### NP4 — Astro dynamic route `[pin].astro` with `getStaticPaths`

**Why new:** No frontend code in repo.
**Reference:** https://docs.astro.build/en/guides/routing/#dynamic-routes
**Pattern:** `getStaticPaths()` reads `parcels.geojson` features, returns `params: { pin }` per feature; static-builds 2,061 parcel detail pages.

### NP5 — JSON-keyed-by-PAMS_PIN overlay format (D-60)

**Why new:** Repo's data convention is parquet; viz overlays are JSON.
**Format:**
```json
{
  "1314_30_1": { "delta_dollars": "1234.56", "tenure_tags": ["tenure_pre_2015", "never_sold"] },
  "1314_30_2": { ... }
}
```
**Apply to:** every `viz/src/data/overlays/<name>.json`. Astro popup component reads ALL overlay JSONs, looks up the clicked PAMS_PIN key, displays union of values.

### NP6 — JSON result file (vs parquet) for CDF gap test verdict

**Why new:** Every other artifact is parquet. CDF gap test's single TRUE/FALSE + 2-3 statistics doesn't merit parquet.
**Pattern:** Use atomic-write JSON helper (S1). Schema: `{ "verdict": bool, "test_name": "mann_whitney_u", "statistic": float, "p_value": float, "n_inside_band": int, "n_outside_band": int, "ratio_band": [0.95, 1.05], "scope_window": [2014, 2025] }`.

---

## No Analog Found

| File | Role | Data Flow | Reason | Mitigation |
|------|------|-----------|--------|------------|
| `viz/astro.config.mjs` | Astro config | n/a | First Astro file | Use Astro init template + D-59 decisions |
| `viz/package.json` | npm config | n/a | First JS in repo | Standard npm format |
| `viz/src/pages/index.astro` | Astro page | static render | First Astro page | Astro docs |
| `viz/src/pages/parcel/[pin].astro` | dynamic Astro page | static render | First Astro dynamic route | Astro getStaticPaths docs |
| `viz/src/components/ParcelMap.astro` | Astro component | client render | First Leaflet integration | Leaflet quickstart |
| `viz/src/components/VegaChart.astro` | Astro component | client render | First vega-embed | vega-embed docs |
| `viz/src/data/parcels.geojson` | data file | output | First GeoJSON | geopandas `to_file(driver="GeoJSON")` |

For these 7 NEW files, planner should reference **external docs** in PLAN.md action sections rather than in-repo analogs, and explicitly note "no in-repo precedent — establishing new convention".

---

## Metadata

**Analog search scope:** `src/fairhaven_tax/`, `scripts/`, `tests/`, `datasets/`, `Makefile`, `pyproject.toml`
**Files scanned:** ~30 Python modules + Makefile
**Pattern extraction date:** 2026-04-29
