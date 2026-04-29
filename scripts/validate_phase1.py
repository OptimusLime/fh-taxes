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


def _write_failure_doc(results) -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Phase 1 Validation FAILED",
        "",
        f"Generated: {ts}",
        "",
        "One or more validation gates failed (D-09 / D-10 / D-11). The pipeline",
        "exited non-zero. Inspect the gate breakdown below and either:",
        "",
        "1. Re-acquire raw data (URLs may have rotated; check manifest.json).",
        "2. Verify the NJGIN MOD-IV filter set is current ({MUN_CODE_FAIR_HAVEN, "
        "PROPERTY_CLASS_RESIDENTIAL}).",
        "3. If published Fair Haven figures have shifted, update "
        "EXPECTED_PARCEL_COUNT / EXPECTED_AGGREGATE_ASSESSED in constants.py.",
        "",
        "## Gate Results",
        "",
        "| name | expected | actual | tolerance | passed | message |",
        "|------|----------|--------|-----------|--------|---------|",
    ]
    for r in results:
        lines.append(
            f"| {r.name} | {r.expected} | {r.actual} | "
            f"{r.tolerance if r.tolerance is not None else '-'} | "
            f"{r.passed} | {r.message} |"
        )
    FAIL_FILE.write_text("\n".join(lines) + "\n")


def main() -> int:
    parcels_path = PROCESSED / "parcels.parquet"
    sales_path = PROCESSED / "sales.parquet"
    if not parcels_path.exists() or not sales_path.exists():
        print(
            f"ERROR: missing {parcels_path} or {sales_path}; run `make ingest` first.",
            file=sys.stderr,
        )
        return 1

    parcels = read_geoparquet(parcels_path)
    sales = read_parquet(sales_path)
    ok, results = run_all_gates(parcels, sales)

    if not ok:
        _write_failure_doc(results)
        print("VALIDATION FAILED — see data/processed/_VALIDATION-FAILED.md", file=sys.stderr)
        for r in results:
            status = "PASS" if r.passed else "FAIL"
            print(f"  [{status}] {r.name}: {r.message}", file=sys.stderr)
        sys.exit(1)

    # Cleanup: remove stale failure doc on success
    if FAIL_FILE.exists():
        FAIL_FILE.unlink()
    print("Validation PASSED")
    for r in results:
        print(f"  [PASS] {r.name}: {r.message}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
