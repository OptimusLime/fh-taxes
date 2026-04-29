#!/usr/bin/env python
"""Ingest SR1A 2018-2025 → data/processed/{sales,rejections}.parquet."""
from __future__ import annotations

import sys
from pathlib import Path

from fairhaven_tax.ingest.manifest import verify_manifest
from fairhaven_tax.ingest.sr1a.parse import parse_sr1a_all
from fairhaven_tax.persist.parquet_io import write_parquet


def _latest_snapshot() -> Path:
    base = Path("data/raw/sr1a")
    if not base.exists():
        raise FileNotFoundError(f"missing {base}; run `make acquire-sr1a`")
    snaps = sorted([d for d in base.iterdir() if d.is_dir()])
    if not snaps:
        raise FileNotFoundError(f"no snapshots in {base}")
    return snaps[-1]


def main() -> int:
    try:
        snap = _latest_snapshot()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    ok, errors = verify_manifest(snap)
    if not ok:
        print(f"ERROR: manifest verification failed in {snap}:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 2

    sales, rej = parse_sr1a_all(snap)
    write_parquet(sales, "data/processed/sales.parquet")
    write_parquet(rej, "data/processed/rejections.parquet")
    print(f"Wrote {len(sales)} sales rows; {len(rej)} rejection rows")
    if len(sales) == 0:
        print("ERROR: zero arms-length sales after filter — refusing to declare success",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
