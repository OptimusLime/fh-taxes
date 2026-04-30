#!/usr/bin/env python
"""Phase 2 validation gate driver (D-58 Plan 1).

Loads data/processed/{prc,sales,parcels,modiv_history}.parquet, runs the
Phase-2 gates, extends validation_report.parquet with source='phase2' rows,
and exits with POSIX-correct codes:

  0 — all gates passed
  1 — at least one gate failed (writes _VALIDATION-FAILED.md)
  2 — preflight failure (one or more input parquets missing)
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from fairhaven_tax.persist.parquet_io import read_parquet
from fairhaven_tax.validate.checks import run_phase2_gates


PROCESSED = Path("data/processed")
FAIL_FILE = PROCESSED / "_VALIDATION-FAILED.md"
PRC = PROCESSED / "prc.parquet"
SALES = PROCESSED / "sales.parquet"
PARCELS = PROCESSED / "parcels.parquet"
MODIV = PROCESSED / "modiv_history.parquet"


def _write_failure_doc(results) -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Phase 2 Validation FAILED",
        "",
        f"Generated: {ts}",
        "",
        "One or more Phase-2 validation gates failed (D-58 Plan 1). The pipeline",
        "exited non-zero. Inspect the gate breakdown below and either:",
        "",
        "1. Re-acquire raw data (URLs may have rotated; check manifest.json).",
        "2. Verify upstream Phase-1.5 builders ran cleanly (build_prc_parquet,",
        "   build_modiv_history).",
        "3. If Fair Haven schema or coverage has shifted, update Phase-2",
        "   thresholds in src/fairhaven_tax/constants.py.",
        "",
        "## Failed Gates",
        "",
    ]
    for r in results:
        if not r.passed:
            lines.append(f"- **{r.name}**: {r.message}")
    lines.append("")
    lines.append("## All Gate Results")
    lines.append("")
    lines.append("| name | expected | actual | tolerance | passed | message |")
    lines.append("|------|----------|--------|-----------|--------|---------|")
    for r in results:
        lines.append(
            f"| {r.name} | {r.expected} | {r.actual} | "
            f"{r.tolerance if r.tolerance is not None else '-'} | "
            f"{r.passed} | {r.message} |"
        )
    FAIL_FILE.write_text("\n".join(lines) + "\n")


def main() -> int:
    missing = [p for p in (PRC, SALES, PARCELS, MODIV) if not p.exists()]
    if missing:
        print(
            "ERROR: missing required inputs: "
            + ", ".join(str(p) for p in missing)
            + "; run Phase-1 + Phase-1.5 builders first.",
            file=sys.stderr,
        )
        return 2

    prc = read_parquet(PRC)
    sales = read_parquet(SALES)
    modiv = read_parquet(MODIV)

    ok, results = run_phase2_gates(prc, sales, modiv)

    if not ok:
        _write_failure_doc(results)
        print("VALIDATION FAILED — see data/processed/_VALIDATION-FAILED.md",
              file=sys.stderr)
        for r in results:
            status = "PASS" if r.passed else "FAIL"
            print(f"  [{status}] {r.name}: {r.message}", file=sys.stderr)
        return 1

    if FAIL_FILE.exists():
        FAIL_FILE.unlink()
    print(f"Phase-2 validation PASSED — {len(results)} gates")
    for r in results:
        print(f"  [PASS] {r.name}: {r.message}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
