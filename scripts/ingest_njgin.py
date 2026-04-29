#!/usr/bin/env python
"""Ingest NJGIN Monmouth Parcels + MOD-IV FGDB → data/processed/parcels.parquet.

The FGDB has TWO layers:
    - "parcels":  geometry + PAMS_PIN, fields: MUN, BLOCK, LOT, QCODE, ...
    - "tax_list": MOD-IV attributes (no geometry), keyed by GIS_PIN.

This script joins them on parcels.PAMS_PIN == tax_list.GIS_PIN, filters to
Fair Haven (MUN/CD_CODE = 1314) class-2 residential, asserts the parcels
layer is in EPSG:3424 (D-13 / D-15), and writes a single GeoParquet file.
"""
from __future__ import annotations

import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

import fiona
import geopandas as gpd
import pandas as pd
from shapely.geometry import shape

from fairhaven_tax import constants
from fairhaven_tax.ingest import njgin
from fairhaven_tax.ingest.manifest import verify_manifest
from fairhaven_tax.persist.parquet_io import write_geoparquet


def _to_decimal(v) -> Decimal | None:
    if v is None:
        return None
    try:
        s = str(v).strip().replace("$", "").replace(",", "")
        if s.lower() in {"nan", "none", ""}:
            return None
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _to_int(v) -> int | None:
    if v is None:
        return None
    try:
        s = str(v).strip()
        if s.lower() in {"nan", "none", ""}:
            return None
        n = int(float(s))
        return n if n > 0 else None
    except (ValueError, TypeError):
        return None


def _yymmdd_to_date(s):
    """MOD-IV DEED_DATE is YYMMDD string. Year < 50 → 20xx; >= 50 → 19xx."""
    if s is None:
        return None
    s = str(s).strip()
    if len(s) != 6 or not s.isdigit() or s == "000000":
        return None
    yy, mm, dd = int(s[0:2]), int(s[2:4]), int(s[4:6])
    yyyy = 2000 + yy if yy < 50 else 1900 + yy
    try:
        from datetime import date
        return date(yyyy, mm, dd)
    except ValueError:
        return None


def _latest_snapshot() -> Path:
    base = Path("data/raw/njgin_monmouth_parcels")
    if not base.exists():
        raise FileNotFoundError(f"missing {base}; run `make acquire-njgin`")
    snaps = sorted([d for d in base.iterdir() if d.is_dir()])
    if not snaps:
        raise FileNotFoundError(f"no snapshots in {base}")
    return snaps[-1]


def _find_gdb(snap: Path) -> Path:
    direct = snap / njgin.GDB_DIRNAME
    if direct.exists():
        return direct
    # Try extracting the zip
    import zipfile
    zips = list(snap.glob("*.zip"))
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            zf.extractall(snap)
    if direct.exists():
        return direct
    # Fallback: search for any *.gdb
    for child in snap.rglob("*.gdb"):
        if child.is_dir():
            return child
    raise FileNotFoundError(f"no .gdb in {snap}")


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

    gdb = _find_gdb(snap)
    layers = fiona.listlayers(str(gdb))
    if njgin.PARCELS_LAYER not in layers or njgin.TAX_LIST_LAYER not in layers:
        print(
            f"ERROR: expected layers {njgin.PARCELS_LAYER!r} and {njgin.TAX_LIST_LAYER!r}, "
            f"got {layers}",
            file=sys.stderr,
        )
        return 2

    # --- Read parcels layer (geometry) ---
    print(f"Reading parcels layer from {gdb}...")
    parcels_records: list[dict] = []
    with fiona.open(str(gdb), layer=njgin.PARCELS_LAYER) as src:
        # CRS check (D-13 / D-15)
        crs_str = str(src.crs).upper()
        if "3424" not in crs_str and "EPSG:3424" not in crs_str:
            # fiona may report as a CRS dict; use the EPSG code if available
            try:
                epsg = src.crs.to_epsg() if hasattr(src.crs, "to_epsg") else None
            except Exception:
                epsg = None
            if epsg != 3424:
                print(
                    f"ERROR: parcels layer CRS is {src.crs}, expected EPSG:3424 (D-15)",
                    file=sys.stderr,
                )
                return 2

        for r in src:
            p = r["properties"]
            if p.get("MUN") != constants.MUN_CODE_FAIR_HAVEN:
                continue
            geom = shape(r["geometry"]) if r["geometry"] else None
            parcels_records.append({
                "pams_pin": p.get("PAMS_PIN"),
                "mun": p.get("MUN"),
                "block": p.get("BLOCK"),
                "lot": p.get("LOT"),
                "qcode": p.get("QCODE") or "",
                "shape_area_sqft": p.get("Shape_Area"),
                "shape_length_ft": p.get("Shape_Length"),
                "geometry": geom,
            })

    parcels_gdf = gpd.GeoDataFrame(parcels_records, geometry="geometry", crs="EPSG:3424")
    print(f"  Fair Haven parcels (geometry): {len(parcels_gdf)}")

    # --- Read tax_list layer (MOD-IV attributes) ---
    print(f"Reading tax_list layer from {gdb}...")
    tl_records: list[dict] = []
    with fiona.open(str(gdb), layer=njgin.TAX_LIST_LAYER) as src:
        for r in src:
            p = r["properties"]
            if p.get("CD_CODE") != constants.MUN_CODE_FAIR_HAVEN:
                continue
            if p.get("PROP_CLASS") != constants.PROPERTY_CLASS_RESIDENTIAL:
                continue
            tl_records.append({
                "gis_pin":              p.get("GIS_PIN"),
                "cd_code":              p.get("CD_CODE"),
                "tl_block":             p.get("BLOCK"),
                "tl_lot":               p.get("LOT"),
                "tl_qualifier":         p.get("QUALIFIER") or "",
                "property_class":       p.get("PROP_CLASS"),
                "property_location":    p.get("PROP_LOC"),
                "land_value":           _to_decimal(p.get("LAND_VAL")),
                "improvement_value":    _to_decimal(p.get("IMPRVT_VAL")),
                "assessed_value":       _to_decimal(p.get("NET_VALUE")),
                "last_year_tax":        _to_decimal(p.get("LAST_YR_TX")),
                "bldg_desc":            p.get("BLDG_DESC"),
                "land_desc":            p.get("LAND_DESC"),
                "lot_size_acres":       _to_decimal(p.get("CALC_ACRE")),
                "prop_use":             p.get("PROP_USE"),
                "bldg_class":           p.get("BLDG_CLASS"),
                "deed_book":            p.get("DEED_BOOK"),
                "deed_page":            p.get("DEED_PAGE"),
                "modiv_last_sale_date": _yymmdd_to_date(p.get("DEED_DATE")),
                "year_built":           _to_int(p.get("YR_CONSTR")),
                "modiv_last_sale_nu_code": p.get("SALES_CODE"),
                "modiv_last_sale_price": _to_decimal(p.get("SALE_PRICE")),
                "dwellings":            _to_int(p.get("DWELL")),
                "comm_dwellings":       _to_int(p.get("COMM_DWELL")),
            })
    tax_list_df = pd.DataFrame(tl_records)
    print(f"  Fair Haven class-2 tax_list records: {len(tax_list_df)}")

    # --- Inner join on PAMS_PIN ↔ GIS_PIN ---
    out = parcels_gdf.merge(
        tax_list_df, left_on="pams_pin", right_on="gis_pin", how="inner",
    )
    # Drop the redundant gis_pin / tl_block / tl_lot / tl_qualifier columns
    out = out.drop(columns=["gis_pin", "tl_block", "tl_lot", "tl_qualifier", "cd_code"])
    out = gpd.GeoDataFrame(out, geometry="geometry", crs="EPSG:3424")

    print(f"  Joined parcels (residential class-2 with geometry): {len(out)}")

    # Add downstream-friendly canonical columns
    out["district"] = constants.SR1A_DISTRICT_FAIR_HAVEN
    out["waterfront_flag"] = False  # MOD-IV does not carry this; Phase 2 may derive
    out["bedrooms"] = None          # not in MOD-IV
    out["bathrooms"] = None         # not in MOD-IV
    # Resolved last-sale columns are filled by reconcile.py (Plan 2 successor)
    out["last_sale_date"] = None
    out["last_sale_price"] = None
    out["last_sale_nu_code"] = None
    out["last_sale_source"] = None

    out_path = Path("data/processed/parcels.parquet")
    write_geoparquet(out, out_path)
    print(f"Wrote {len(out)} parcels → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
