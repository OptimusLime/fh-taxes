#!/usr/bin/env python
"""Ingest NJGIN Monmouth Parcels + MOD-IV FGDB → data/processed/parcels.parquet.

D-13: persists in EPSG:3424. D-15: hard-fails on CRS mismatch.
D-11/D-12: filters MUN_CODE == "1314" AND PROPERTY_CLASS == "2".
"""
from __future__ import annotations

import re
import sys
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

from fairhaven_tax import constants
from fairhaven_tax.ingest.manifest import verify_manifest
from fairhaven_tax.ingest.pams_pin import build_pams_pin
from fairhaven_tax.persist.parquet_io import write_geoparquet


# Column-alias resolver: canonical → list of candidate source aliases.
COLUMN_ALIASES: dict[str, list[str]] = {
    "MUN_CODE": ["MUN_CODE", "mun_code", "MUNCODE"],
    "PROPERTY_CLASS": ["PROPERTY_CLASS", "PROP_CLASS", "PROPCLASS"],
    "BLOCK": ["BLOCK", "BLK"],
    "LOT": ["LOT"],
    "QUALIFIER": ["QUALIFIER", "QUAL"],
    "NET_VALUE": ["NET_VALUE", "TOTAL_VALUE", "ASSESSED_VALUE", "TOTAL_ASSMNT"],
    "LAND_VALUE": ["LAND_VALUE", "LAND_VAL"],
    "IMPROVEMENT_VALUE": ["IMPROVEMENT_VALUE", "IMP_VALUE", "BLDG_VAL"],
    "YR_CONSTR": ["YR_CONSTR", "YEAR_BUILT", "YRBUILT"],
    "BLDG_SQFT": ["BLDG_SQFT", "SQFT", "SQ_FT", "BUILDING_SF"],
    "ACREAGE": ["ACREAGE", "ACRES", "LOT_ACRES"],
    "MODIV_SALE_DATE": ["LAST_SALE_DATE", "SALE_DATE", "DEED_DATE"],
    "MODIV_SALE_PRICE": ["LAST_SALE_PRICE", "SALE_PRICE", "DEED_PRICE"],
    "MODIV_SALE_NU_CODE": ["LAST_NU_CODE", "NU_CODE", "DEED_NU"],
}
REQUIRED_CANONICAL = ["MUN_CODE", "PROPERTY_CLASS", "BLOCK", "LOT", "NET_VALUE"]


def _resolve_columns(present: list[str]) -> dict[str, str]:
    """Given the set of columns actually present in the FGDB, return canonical → source mapping."""
    upper = {c.upper(): c for c in present}
    resolved: dict[str, str] = {}
    for canonical, candidates in COLUMN_ALIASES.items():
        for cand in candidates:
            if cand.upper() in upper:
                resolved[canonical] = upper[cand.upper()]
                break
    return resolved


def _to_decimal(v) -> Decimal | None:
    if v is None:
        return None
    try:
        s = str(v)
        if s.lower() in {"nan", "none", ""}:
            return None
        s = s.replace("$", "").replace(",", "").strip()
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
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _latest_snapshot(source: str) -> Path:
    base = Path("data/raw") / source
    if not base.exists():
        raise FileNotFoundError(
            f"missing snapshot dir: {base}. Run `make acquire-njgin` first."
        )
    snaps = sorted([d for d in base.iterdir() if d.is_dir()])
    if not snaps:
        raise FileNotFoundError(f"no snapshots in {base}")
    return snaps[-1]


def _find_or_extract_gdb(snap: Path) -> Path:
    gdbs = list(snap.glob("*.gdb"))
    if gdbs:
        return gdbs[0]
    # Try to extract any zip
    zips = list(snap.glob("*.zip"))
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            zf.extractall(snap)
    gdbs = list(snap.glob("*.gdb"))
    if gdbs:
        return gdbs[0]
    # Some FGDBs nest inside a top-level dir
    for child in snap.iterdir():
        if child.is_dir():
            gdbs = list(child.glob("*.gdb"))
            if gdbs:
                return gdbs[0]
    raise FileNotFoundError(f"no .gdb directory in {snap}")


def main() -> int:
    import fiona
    import geopandas as gpd

    try:
        snap = _latest_snapshot("njgin_monmouth_parcels")
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    ok, errors = verify_manifest(snap)
    if not ok:
        print(f"ERROR: manifest verification failed in {snap}:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 2

    try:
        gdb = _find_or_extract_gdb(snap)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    layers = fiona.listlayers(str(gdb))
    layer = next(
        (l for l in layers if re.search(r"parcel.*modiv", l, re.IGNORECASE)),
        layers[0],
    )
    print(f"Reading layer: {layer} from {gdb}")
    gdf = gpd.read_file(str(gdb), layer=layer)

    if gdf.crs is None:
        print(
            f"ERROR: input has no CRS; D-15 requires {constants.CRS_NATIVE}",
            file=sys.stderr,
        )
        return 2
    crs_str = str(gdf.crs).upper()
    expected = constants.CRS_NATIVE.upper()
    # ESRI:103504 is the proprietary code for the same NAD83 NJ State Plane.
    if expected not in crs_str and "103504" not in crs_str and "3424" not in crs_str:
        print(
            f"ERROR: input CRS is {gdf.crs}, expected {constants.CRS_NATIVE} (D-15)",
            file=sys.stderr,
        )
        return 2

    resolved = _resolve_columns(list(gdf.columns))
    missing = [c for c in REQUIRED_CANONICAL if c not in resolved]
    if missing:
        print(
            f"ERROR: required columns missing from FGDB: {missing}. "
            f"Update COLUMN_ALIASES in scripts/ingest_njgin.py.",
            file=sys.stderr,
        )
        return 2

    # Filter
    mun_col = resolved["MUN_CODE"]
    pc_col = resolved["PROPERTY_CLASS"]
    gdf = gdf[
        (gdf[mun_col].astype(str).str.strip() == constants.MUN_CODE_FAIR_HAVEN)
        & (gdf[pc_col].astype(str).str.strip() == constants.PROPERTY_CLASS_RESIDENTIAL)
    ].copy()

    # Build canonical schema
    out = gpd.GeoDataFrame(geometry=gdf.geometry.values, crs=gdf.crs)
    out["mun_code"] = constants.MUN_CODE_FAIR_HAVEN
    out["district"] = constants.SR1A_DISTRICT_FAIR_HAVEN
    out["block"] = gdf[resolved["BLOCK"]].astype(str).str.strip()
    out["lot"] = gdf[resolved["LOT"]].astype(str).str.strip()
    out["qualifier"] = (
        gdf[resolved["QUALIFIER"]].astype(str).str.strip()
        if "QUALIFIER" in resolved
        else ""
    )
    out["qualifier"] = out["qualifier"].where(
        ~out["qualifier"].str.lower().isin(["none", "nan", ""]), ""
    )
    out["pams_pin"] = [
        build_pams_pin(d, b, l, q)
        for d, b, l, q in zip(out["district"], out["block"], out["lot"], out["qualifier"])
    ]
    out["property_class"] = constants.PROPERTY_CLASS_RESIDENTIAL
    out["assessed_value"] = [_to_decimal(v) for v in gdf[resolved["NET_VALUE"]]]
    out["land_value"] = (
        [_to_decimal(v) for v in gdf[resolved["LAND_VALUE"]]]
        if "LAND_VALUE" in resolved else None
    )
    out["improvement_value"] = (
        [_to_decimal(v) for v in gdf[resolved["IMPROVEMENT_VALUE"]]]
        if "IMPROVEMENT_VALUE" in resolved else None
    )
    out["year_built"] = (
        [_to_int(v) for v in gdf[resolved["YR_CONSTR"]]]
        if "YR_CONSTR" in resolved else None
    )
    out["sqft"] = (
        [_to_int(v) for v in gdf[resolved["BLDG_SQFT"]]]
        if "BLDG_SQFT" in resolved else None
    )
    out["lot_size_acres"] = (
        [_to_decimal(v) for v in gdf[resolved["ACREAGE"]]]
        if "ACREAGE" in resolved else None
    )
    out["bedrooms"] = None
    out["bathrooms"] = None
    out["waterfront_flag"] = False

    # MOD-IV last sale (raw passthrough)
    if "MODIV_SALE_DATE" in resolved:
        import pandas as pd
        out["modiv_last_sale_date"] = pd.to_datetime(
            gdf[resolved["MODIV_SALE_DATE"]], errors="coerce"
        ).dt.date
    else:
        out["modiv_last_sale_date"] = None
    out["modiv_last_sale_price"] = (
        [_to_decimal(v) for v in gdf[resolved["MODIV_SALE_PRICE"]]]
        if "MODIV_SALE_PRICE" in resolved else None
    )
    out["modiv_last_sale_nu_code"] = (
        [str(v).strip() if v is not None else None for v in gdf[resolved["MODIV_SALE_NU_CODE"]]]
        if "MODIV_SALE_NU_CODE" in resolved else None
    )

    # Resolved last-sale columns are populated by reconcile.py (Task 2)
    out["last_sale_date"] = None
    out["last_sale_price"] = None
    out["last_sale_nu_code"] = None
    out["last_sale_source"] = None

    out_path = Path("data/processed/parcels.parquet")
    write_geoparquet(out, out_path)
    print(f"Wrote {len(out)} parcels to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
