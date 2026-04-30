#!/usr/bin/env python3
"""Build viz/src/data/parcels_full.json — one structured record per parcel.

Joins parcels.parquet + prc.parquet + sales.parquet + modiv_history.parquet
into a single per-PIN dict with logical sections (identity, building,
assessment, sales_history, history, data_quality). Powers the click-to-open
drawer in viz/src/components/ParcelDrawer.

Phase 2 internal-use only — owner_mailing_address from Bloustein is included.
Phase 3 publication pipeline will strip sensitive fields at static-build time.
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PARCELS = ROOT / "data" / "processed" / "parcels.parquet"
PRC = ROOT / "data" / "processed" / "prc.parquet"
SALES = ROOT / "data" / "processed" / "sales.parquet"
MODIV_HIST = ROOT / "data" / "processed" / "modiv_history.parquet"
DATA_QUALITY_OVERLAY = ROOT / "viz" / "src" / "data" / "overlays" / "data_quality.json"
OUT = ROOT / "viz" / "src" / "data" / "parcels_full.json"


def _clean(v):
    """Convert to JSON-safe primitive; drop NaN/empty/'nan' strings."""
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, Decimal):
        # Money/area Decimals → float for JSON. Lose Decimal precision at the
        # presentation boundary; data/processed/*.parquet remains canonical.
        try:
            return float(v)
        except Exception:
            return str(v)
    if isinstance(v, str):
        s = v.strip()
        if not s or s.lower() == "nan" or s.lower() == "none":
            return None
        return s
    if hasattr(v, "isoformat"):
        return v.isoformat()
    # numpy/pandas array-like → list of cleaned scalars
    if hasattr(v, "tolist") and not isinstance(v, str):
        try:
            seq = v.tolist()
            if isinstance(seq, list):
                return [_clean(x) for x in seq if _clean(x) not in (None, "")]
            return _clean(seq)
        except Exception:
            pass
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v if _clean(x) not in (None, "")]
    if hasattr(v, "item"):
        try:
            v = v.item()
        except Exception:
            pass
    return v


def _row_to_dict(row, cols):
    """Pull selected columns from a Series, cleaning each value."""
    out = {}
    for c in cols:
        out[c] = _clean(row.get(c) if hasattr(row, "get") else row[c])
    return out


def main() -> int:
    for path in (PARCELS, PRC, SALES, MODIV_HIST):
        if not path.exists():
            print(f"ERROR: missing input: {path}", file=sys.stderr)
            return 2

    parcels = pd.read_parquet(PARCELS)
    if "geometry" in parcels.columns:
        parcels = parcels.drop(columns=["geometry"])
    prc = pd.read_parquet(PRC)
    sales = pd.read_parquet(SALES)
    hist = pd.read_parquet(MODIV_HIST)

    # Index sales by parcel_pin for fast lookup
    sales_by_pin: dict[str, list[dict]] = defaultdict(list)
    for _, r in sales.iterrows():
        pin = _clean(r.get("parcel_pin"))
        if not pin:
            continue
        sales_by_pin[pin].append(
            {
                "sale_date": _clean(r.get("sale_date")),
                "sale_price": _clean(r.get("sale_price")),
                "nu_code": _clean(r.get("nu_code")),
                "deed_book": _clean(r.get("deed_book")),
                "deed_page": _clean(r.get("deed_page")),
                "grantor": _clean(r.get("grantor")),
                "grantee": _clean(r.get("grantee")),
                "family_sale_flag": _clean(r.get("family_sale_flag")),
                "sales_ratio_assessor": _clean(r.get("sales_ratio_assessor")),
                "remarks": _clean(r.get("remarks")),
                "source": "SR1A+sr.cgi",
                "source_year": _clean(r.get("source_year")),
            }
        )

    # Index history (37-year trajectory) by parcel_pin
    hist_by_pin: dict[str, list[dict]] = defaultdict(list)
    for _, r in hist.sort_values(["parcel_pin", "year"]).iterrows():
        pin = _clean(r.get("parcel_pin"))
        if not pin:
            continue
        hist_by_pin[pin].append(
            {
                "year": int(r["year"]) if pd.notna(r.get("year")) else None,
                "land_value": _clean(r.get("land_value")),
                "improvement_value": _clean(r.get("improvement_value")),
                "net_value": _clean(r.get("net_value")),
                "deductions": _clean(r.get("deductions")),
                "sale_price": _clean(r.get("sale_price")),
                "sale_assessment": _clean(r.get("sale_assessment")),
                "sale_nu_code": _clean(r.get("sale_nu_code")),
                "deed_date": _clean(r.get("deed_date")),
                "deed_book": _clean(r.get("deed_book")),
                "deed_page": _clean(r.get("deed_page")),
                "owner_mailing_address": _clean(r.get("owner_mailing_address")),
                "building_description": _clean(r.get("building_description")),
            }
        )

    # PRC by pams_pin
    prc_by_pin = {p: row for p, row in zip(prc["pams_pin"], prc.to_dict(orient="records"))}

    # Data-quality overlay
    if DATA_QUALITY_OVERLAY.exists():
        with open(DATA_QUALITY_OVERLAY) as f:
            dq = json.load(f)
    else:
        dq = {}

    # Build per-parcel records
    out: dict[str, dict] = {}
    for _, p in parcels.iterrows():
        pin = _clean(p.get("pams_pin"))
        if not pin:
            continue

        prc_row = prc_by_pin.get(pin, {})
        sales_records = sales_by_pin.get(pin, [])
        hist_records = hist_by_pin.get(pin, [])

        # Latest year of history (the 2025 row typically)
        latest_hist = hist_records[-1] if hist_records else {}

        # Assemble the record
        record: dict = {
            "identity": {
                "pams_pin": pin,
                "block": _clean(p.get("block")),
                "lot": _clean(p.get("lot")),
                "qualifier": _clean(p.get("qcode")) or _clean(prc_row.get("qualifier")),
                "property_location": _clean(p.get("property_location")),
                "owner_mailing_address": _clean(latest_hist.get("owner_mailing_address")),
                "zone": _clean(prc_row.get("zone")),
                "map_page": _clean(prc_row.get("map_page")),
                "property_class": _clean(p.get("property_class")),
                "bldg_class": _clean(p.get("bldg_class")),
                "district": _clean(p.get("district")),
                "waterfront": bool(p.get("waterfront_flag")) if pd.notna(p.get("waterfront_flag")) else False,
            },
            "lot_geometry": {
                "shape_area_sqft": _clean(p.get("shape_area_sqft")),
                "shape_length_ft": _clean(p.get("shape_length_ft")),
                "lot_size_acres": _clean(p.get("lot_size_acres")) or _clean(prc_row.get("acreage")),
                "land_desc": _clean(prc_row.get("land_desc")) or _clean(p.get("land_desc")),
            },
            "building": {
                "year_built": _clean(prc_row.get("year_built")) or _clean(p.get("year_built")),
                "eff_age": _clean(prc_row.get("eff_age")),
                "style_code": _clean(prc_row.get("style_code")),
                "bldg_desc": _clean(prc_row.get("bldg_desc")) or _clean(p.get("bldg_desc")),
                "square_ft": _clean(prc_row.get("square_ft")),
                "livable_area": _clean(prc_row.get("livable_area")),
                "first_story_sf": _clean(prc_row.get("first_story_sf")),
                "upper_story_sf": _clean(prc_row.get("upper_story_sf")),
                "half_story_sf": _clean(prc_row.get("half_story_sf")),
                "bedrooms": _clean(prc_row.get("bedrooms")) or _clean(p.get("bedrooms")),
                "bathrooms": _clean(prc_row.get("bathrooms")) or _clean(p.get("bathrooms")),
                "room_count": _clean(prc_row.get("room_count")),
                "kitchens": _clean(prc_row.get("kitchens")),
                "fireplaces": _clean(prc_row.get("fireplaces")),
                "condition": _clean(prc_row.get("condition")),
                "quality_grade": _clean(prc_row.get("quality_grade")),
                "foundation": _clean(prc_row.get("foundation")),
                "exterior": _clean(prc_row.get("exterior")),
                "roof_type": _clean(prc_row.get("roof_type")),
                "roof_material": _clean(prc_row.get("roof_material")),
                "heating_type": _clean(prc_row.get("heating_type")),
                "heating_sf": _clean(prc_row.get("heating_sf")),
                "ac_type": _clean(prc_row.get("ac_type")),
                "ac_sf": _clean(prc_row.get("ac_sf")),
                "garage_type": _clean(prc_row.get("garage_type")),
                "garage_sf": _clean(prc_row.get("garage_sf")),
                "porch_sf": _clean(prc_row.get("porch_sf")),
                "patio_sf": _clean(prc_row.get("patio_sf")),
                "shed_sf": _clean(prc_row.get("shed_sf")),
                "sewer": _clean(prc_row.get("sewer")),
                "water": _clean(prc_row.get("water")),
                "gas": _clean(prc_row.get("gas")),
                "topography": _clean(prc_row.get("topography")),
                "road_type": _clean(prc_row.get("road_type")),
                "dwellings": _clean(p.get("dwellings")),
            },
            "current_assessment": {
                "land_value": _clean(p.get("land_value")),
                "improvement_value": _clean(p.get("improvement_value")),
                "net_value": _clean(p.get("assessed_value")),
                "last_year_tax": _clean(p.get("last_year_tax")),
                "current_year_assessment_ch75": _clean(prc_row.get("current_year_assessment")),
                "prior_year_assessment_ch75": _clean(prc_row.get("prior_year_assessment")),
                "assessment_change_pct_ch75": _clean(prc_row.get("assessment_change_pct")),
                "notice_year_ch75": _clean(prc_row.get("notice_year")),
                "actual_tax_paid_total": _clean(prc_row.get("actual_tax_paid_total")),
                "tax_1h_paid": _clean(prc_row.get("tax_1h_paid")),
                "tax_2h_paid": _clean(prc_row.get("tax_2h_paid")),
                "deduction_codes": _clean(prc_row.get("deduction_codes")),
                "deduction_amount": _clean(prc_row.get("deduction_amount")),
            },
            "sales_history": sales_records,
            "modiv_last_sale": {
                "date": _clean(p.get("modiv_last_sale_date")) or _clean(p.get("last_sale_date")),
                "price": _clean(p.get("modiv_last_sale_price")) or _clean(p.get("last_sale_price")),
                "nu_code": _clean(p.get("modiv_last_sale_nu_code")) or _clean(p.get("last_sale_nu_code")),
                "deed_book": _clean(p.get("deed_book")),
                "deed_page": _clean(p.get("deed_page")),
                "source": _clean(p.get("last_sale_source")),
            },
            "history": hist_records,  # 37 years
            "data_quality_flags": dq.get(pin, []),
        }
        out[pin] = record

    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(OUT.suffix + ".tmp")
    with open(tmp, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    tmp.replace(OUT)

    print(f"wrote {len(out)} parcel records to {OUT}")
    print(f"   file size: {OUT.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"   sample PIN with sales: {next((p for p, r in out.items() if r['sales_history']), '(none)')}")
    print(f"   sample PIN with bedrooms: {next((p for p, r in out.items() if r['building'].get('bedrooms')), '(none)')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
