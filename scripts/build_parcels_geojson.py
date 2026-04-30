#!/usr/bin/env python
"""Build viz/src/data/parcels.geojson from data/processed/parcels.parquet (D-60).

Reads the GeoParquet, restricts properties to a stable-identity whitelist
(D-65 footprint isolation — owner names NEVER appear in the published GeoJSON),
reprojects EPSG:3424 → EPSG:4326 (Leaflet wants WGS84), and writes via
atomic .tmp + Path.replace (D-63 hot-reload contract).

Daniel's Law (D-64, D-65): the PROPERTY_COLS whitelist below is the single
enforcement point. Any column not in the list — including owner_name,
owner_mailing_address, or any future owner_* fields — is excluded from the
output GeoJSON by construction. Per-PIN richer data lives in
viz/src/data/overlays/*.json (local-only, scrubbed at Phase 3 build time).

Exit codes (S3):
  0 — success
  2 — preflight failure (missing parquet, zero rows)
"""
from __future__ import annotations

import sys
from pathlib import Path

from fairhaven_tax import constants
from fairhaven_tax.persist.parquet_io import read_geoparquet


BASE = Path("data/processed/parcels.parquet")
OUT = Path("viz/src/data/parcels.geojson")

# D-60 / D-65 — stable-identity columns ONLY. The plan's spec lists
# `pams_pin, block, lot, mun, prop_loc`; the real D-32 schema uses
# `property_location` instead of `prop_loc`. We accept either (whichever
# is present is kept; missing columns are silently dropped).
#
# This whitelist is the Daniel's Law enforcement boundary: owner_name,
# owner_mailing_address, and any other owner_* fields are excluded by
# construction because they are not enumerated here.
PROPERTY_COLS = ["pams_pin", "block", "lot", "mun", "prop_loc", "property_location"]


def main() -> int:
    if not BASE.exists():
        print(
            f"ERROR: missing {BASE}; run `make ingest-njgin` first",
            file=sys.stderr,
        )
        return 2

    gdf = read_geoparquet(BASE)

    # S2: refuse-zero-rows guard.
    if len(gdf) == 0:
        print("ERROR: zero parcels — refusing to declare success", file=sys.stderr)
        return 2

    # D-65 owner-name footprint isolation: restrict properties to whitelist.
    # Any owner_* columns present in the parquet are dropped here.
    keep = [c for c in PROPERTY_COLS if c in gdf.columns] + [gdf.geometry.name]
    gdf = gdf[keep]

    # Reproject EPSG:3424 (NJ State Plane US ft) → EPSG:4326 (WGS84) for Leaflet.
    gdf_wgs = gdf.to_crs(constants.CRS_EXPORT)

    # Atomic write (D-63 hot-reload contract): write to .tmp sibling, then
    # Path.replace() so Astro's Vite watcher sees a single rename event.
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".geojson.tmp")
    if tmp.exists():
        tmp.unlink()
    gdf_wgs.to_file(tmp, driver="GeoJSON")
    tmp.replace(OUT)
    print(f"Wrote {len(gdf_wgs)} features → {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
