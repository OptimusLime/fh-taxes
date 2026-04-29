#!/usr/bin/env python
"""MOD-IV ↔ SR1A reconciliation. Updates parcels.parquet in place; writes
data/processed/reconciliation_diffs.parquet (always)."""
from __future__ import annotations

import sys
from pathlib import Path

from fairhaven_tax.persist.parquet_io import (
    read_geoparquet,
    read_parquet,
    write_geoparquet,
    write_parquet,
)
from fairhaven_tax.validate.reconcile import reconcile_last_sale


def main() -> int:
    parcels_path = Path("data/processed/parcels.parquet")
    sales_path = Path("data/processed/sales.parquet")
    if not parcels_path.exists() or not sales_path.exists():
        print(
            f"ERROR: missing {parcels_path} or {sales_path}. "
            "Run `make ingest-njgin` and `make ingest-sr1a` first.",
            file=sys.stderr,
        )
        return 2
    parcels = read_geoparquet(parcels_path)
    sales = read_parquet(sales_path)
    parcels2, diffs = reconcile_last_sale(parcels, sales)
    write_geoparquet(parcels2, parcels_path)
    write_parquet(diffs, "data/processed/reconciliation_diffs.parquet")
    print(f"Reconciled {len(parcels2)} parcels; {len(diffs)} diffs flagged "
          f"(>180 days OR >5% price)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
