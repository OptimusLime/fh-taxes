#!/usr/bin/env python
"""Build the data-quality Astro viz artifacts (D-58 Plan 1, D-60, D-61, D-63).

Reads:
  data/processed/validation_report.parquet — long-format gate results
  data/processed/prc.parquet                — per-parcel feature frame

Writes (atomically via .tmp + Path.replace):
  viz/src/data/charts/data_quality.vl.json   — Vega-Lite spec from Altair
  viz/src/data/overlays/data_quality.json    — { pams_pin: [issue_tag, ...] }

Exit codes (POSIX):
  0 — success
  2 — preflight failure (input parquet missing or zero-row prc)
"""
from __future__ import annotations

import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

import altair as alt
import pandas as pd

from fairhaven_tax.persist.json_io import atomic_write_json
from fairhaven_tax.persist.parquet_io import read_parquet


VALIDATION_REPORT = Path("data/processed/validation_report.parquet")
PRC = Path("data/processed/prc.parquet")
OUT_CHART = Path("viz/src/data/charts/data_quality.vl.json")
OUT_OVERLAY = Path("viz/src/data/overlays/data_quality.json")


def _to_float(s: object) -> float | None:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    try:
        return float(Decimal(str(s)))
    except (InvalidOperation, ValueError):
        return None


def _build_chart(report_df: pd.DataFrame) -> alt.Chart:
    """Bar chart of actual/expected per gate, coloured by passed."""
    rows = []
    for _, r in report_df.iterrows():
        actual_f = _to_float(r.get("actual"))
        expected_f = _to_float(r.get("expected"))
        if actual_f is None or expected_f is None or expected_f == 0:
            continue
        rows.append({
            "gate_name": str(r.get("gate_name")),
            "actual": actual_f,
            "expected": expected_f,
            "actual_over_expected": actual_f / expected_f,
            "passed": bool(r.get("passed")),
            "message": str(r.get("message", "")),
            "source": str(r.get("source", "phase2")),
        })
    df = pd.DataFrame(rows)
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("gate_name:N", sort="-y", title="Validation gate"),
            y=alt.Y("actual_over_expected:Q", title="Actual / Expected"),
            color=alt.Color(
                "passed:N",
                scale=alt.Scale(domain=[True, False], range=["#2ca02c", "#d62728"]),
            ),
            tooltip=["gate_name", "actual", "expected", "message", "source"],
        )
        .properties(title="Phase 2 Data Quality — Gate Results")
    )
    return chart


_FEATURE_TAG_MAP: tuple[tuple[str, str], ...] = (
    ("livable_area", "missing_livable_area"),
    ("bedrooms", "missing_bedrooms"),
    ("bathrooms", "missing_bathrooms"),
    ("condition", "missing_condition"),
    ("quality_grade", "missing_quality_grade"),
    ("year_built", "missing_year_built"),
)


def _build_overlay(prc_df: pd.DataFrame) -> dict[str, list[str]]:
    """Per-PIN list of issue tags. Empty list when parcel passes all per-row checks."""
    overlay: dict[str, list[str]] = {}

    # Pre-compute negative-assessment column flag if present.
    assess_col = None
    for cand in ("current_year_assessment", "current_assessed_total"):
        if cand in prc_df.columns:
            assess_col = cand
            break

    for _, row in prc_df.iterrows():
        pin = row.get("pams_pin")
        if pin is None:
            continue
        tags: list[str] = []
        for col, tag in _FEATURE_TAG_MAP:
            if col not in prc_df.columns:
                continue
            v = row.get(col)
            if v is None or (isinstance(v, float) and pd.isna(v)):
                tags.append(tag)
        if assess_col is not None:
            v = row.get(assess_col)
            if v is not None and not (isinstance(v, float) and pd.isna(v)):
                try:
                    if float(v) < 0:
                        tags.append("negative_assessment")
                except (TypeError, ValueError):
                    pass
        overlay[str(pin)] = tags
    return overlay


def main() -> int:
    if not VALIDATION_REPORT.exists() or not PRC.exists():
        missing = [str(p) for p in (VALIDATION_REPORT, PRC) if not p.exists()]
        print(f"ERROR: missing inputs: {missing}; run scripts/run_validation.py first.",
              file=sys.stderr)
        return 2

    report = read_parquet(VALIDATION_REPORT)
    prc = read_parquet(PRC)

    if len(prc) == 0:
        print("ERROR: prc.parquet has zero rows — refusing to declare success",
              file=sys.stderr)
        return 2

    # ---- Chart ----
    OUT_CHART.parent.mkdir(parents=True, exist_ok=True)
    chart = _build_chart(report)
    # Altair writes directly; re-route through atomic_write_json to honour D-63.
    raw_path = OUT_CHART.with_suffix(OUT_CHART.suffix + ".raw")
    chart.save(str(raw_path), format="json")
    spec = json.loads(raw_path.read_text())
    raw_path.unlink()
    atomic_write_json(OUT_CHART, spec)

    # ---- Overlay ----
    overlay = _build_overlay(prc)
    if not overlay:
        print("ERROR: empty overlay (no PINs found) — refusing to write",
              file=sys.stderr)
        return 2
    atomic_write_json(OUT_OVERLAY, overlay)

    issue_count = sum(1 for tags in overlay.values() if tags)
    print(
        f"Wrote chart ({len(report)} gate rows) and overlay "
        f"({len(overlay)} PINs, {issue_count} with issues) → {OUT_CHART.parent.parent}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
