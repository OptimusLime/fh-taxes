#!/usr/bin/env python
"""Build data/processed/modiv_history.parquet from Bloustein MOD-IV historical CSVs (D-34).

Walks the latest dated snapshot under data/raw/bloustein_modiv/, calls
parse_bloustein_all, writes a Decimal-preserving parquet keyed (parcel_pin, year).

Refuses to declare success on zero-row output. Emits a one-line summary
(snapshot path, year range, row count) on success.

Note: Bloustein collector does NOT currently write a manifest.json (verified
2026-04-29 in datasets/collect_bloustein.py); this script therefore skips
manifest verification — consistent with how the collector ships.
"""
from __future__ import annotations

import sys
from pathlib import Path

from fairhaven_tax.ingest.bloustein import parse_bloustein_all
from fairhaven_tax.persist.parquet_io import write_parquet


BASE = Path("data/raw/bloustein_modiv")
OUT = Path("data/processed/modiv_history.parquet")


def _latest_snapshot() -> Path:
    if not BASE.exists():
        raise FileNotFoundError(
            f"missing {BASE}; run `python datasets/collect_bloustein.py`"
        )
    snaps = sorted(d for d in BASE.iterdir() if d.is_dir())
    if not snaps:
        raise FileNotFoundError(
            f"no snapshots in {BASE}; run `python datasets/collect_bloustein.py`"
        )
    return snaps[-1]


def main() -> int:
    try:
        snap = _latest_snapshot()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    print(f"Loading Bloustein snapshot: {snap}")
    df = parse_bloustein_all(snap)
    if len(df) == 0:
        print("ERROR: zero rows — refusing to declare success", file=sys.stderr)
        return 2

    write_parquet(df, str(OUT))

    years = sorted(df["year"].unique())
    print(
        f"Wrote {len(df):,} rows ({len(years)} years: {years[0]}-{years[-1]}) → {OUT}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
