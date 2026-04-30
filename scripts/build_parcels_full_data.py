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


# NU codes that mark an arms-length transfer (vs family/foreclosure/etc.).
# Phase 1 convention: blank, "0", "00" all = arms-length.
ARMS_LENGTH_NU = frozenset({"", "0", "00"})


def _is_arms_length(nu) -> bool:
    if nu is None:
        return True
    s = str(nu).strip()
    return s in ARMS_LENGTH_NU


def _build_unified_sales(
    sales_records: list[dict],
    hist_records: list[dict],
) -> list[dict]:
    """Merge SR1A 2018-2025 sales (rich grantor/grantee detail) with the
    full Bloustein deed-event history (1989+), dedup by (deed_date,
    deed_book, deed_page), preferring SR1A when both sources cover the
    same deed. Returns reverse-chronological list.
    """
    by_key: dict[tuple, dict] = {}

    # First pass: SR1A (richer detail; preferred)
    for s in sales_records:
        sd = s.get("sale_date")
        if not sd:
            continue
        key = (str(sd)[:10], s.get("deed_book"), s.get("deed_page"))
        by_key[key] = {
            "date": str(sd)[:10],
            "year": int(str(sd)[:4]) if str(sd)[:4].isdigit() else None,
            "price": s.get("sale_price"),
            "nu_code": s.get("nu_code"),
            "deed_book": s.get("deed_book"),
            "deed_page": s.get("deed_page"),
            "grantor": s.get("grantor"),
            "grantee": s.get("grantee"),
            "family_sale": bool(s.get("family_sale_flag")),
            "sales_ratio_assessor": s.get("sales_ratio_assessor"),
            "remarks": s.get("remarks"),
            "is_arms_length": _is_arms_length(s.get("nu_code")),
            "source": "SR1A+sr.cgi",
        }

    # Second pass: Bloustein historical deed events (dedup by key)
    seen_hist: set[tuple] = set()
    for h in hist_records:
        deed_date = h.get("deed_date")
        if not deed_date:
            continue
        sp = h.get("sale_price")
        if sp is None:
            continue
        try:
            sp_n = float(sp)
        except (TypeError, ValueError):
            continue
        key = (str(deed_date)[:10], h.get("deed_book"), h.get("deed_page"))
        if key in seen_hist:
            continue
        seen_hist.add(key)
        if key in by_key:
            # SR1A already covers this; just augment sale_assessment if missing
            if "sale_assessment" not in by_key[key]:
                by_key[key]["sale_assessment"] = h.get("sale_assessment")
            continue
        by_key[key] = {
            "date": str(deed_date)[:10],
            "year": int(str(deed_date)[:4]) if str(deed_date)[:4].isdigit() else None,
            "price": sp_n if sp_n > 0 else None,
            "nu_code": h.get("sale_nu_code"),
            "deed_book": h.get("deed_book"),
            "deed_page": h.get("deed_page"),
            "sale_assessment": h.get("sale_assessment"),
            "is_arms_length": _is_arms_length(h.get("sale_nu_code")) and (sp_n is not None and sp_n > 1000),
            "source": "Bloustein",
        }

    sales = list(by_key.values())
    # Sort reverse-chrono by date
    sales.sort(key=lambda s: s.get("date") or "", reverse=True)
    return sales


def _cohort_tags(
    latest_arms_year: int | None,
    latest_any_deed_year: int | None,
) -> dict:
    """Multi-tag cohort assignment.

    Primary `cohort` = tenure window keyed off LATEST DEED EVENT OF ANY KIND
    (arms-length OR family/exempt transfer) — matches what the legend label
    "last sold" intuitively means to a viewer of the map.

    Orthogonal flags:
      - `non_arms_only`: parcel has deed events but NEVER an arms-length sale.
        Critical for assessment analysis: assessor has no market price anchor.
      - `no_deed_since_1989`: zero deed events on record. Truly never traded.
    """
    tags: list[str] = []

    # Bucket by the latest deed event (any kind). If none at all, fall into
    # the dedicated "no_deed_since_1989" cohort.
    bucket_year = latest_any_deed_year
    if bucket_year is None:
        cohort = "no_deed_since_1989"
        tags.append("no_deed_since_1989")
        tags.append("tenure_pre_2015")  # by definition predates 2015
    elif bucket_year < 2015:
        cohort = "tenure_pre_2015"
        tags.append("tenure_pre_2015")
    elif bucket_year < 2020:
        cohort = "tenure_2015_2019"
        tags.append("tenure_2015_2019")
    elif bucket_year < 2023:
        cohort = "tenure_pandemic_2020_2022"
        tags.append("tenure_pandemic_2020_2022")
    else:
        cohort = "tenure_post_pandemic_2023plus"
        tags.append("tenure_post_pandemic_2023plus")

    # Orthogonal: did this parcel ever have an arms-length sale on record?
    if latest_arms_year is None and latest_any_deed_year is not None:
        tags.append("non_arms_only")

    return {
        "cohort": cohort,
        "tags": tags,
        "latest_arms_length_year": latest_arms_year,
        "latest_any_deed_year": latest_any_deed_year,
        "non_arms_only": (latest_arms_year is None and latest_any_deed_year is not None),
        "no_deed_since_1989": (latest_any_deed_year is None),
    }


def _latest_any_deed_year(
    sales_records: list[dict],
    hist_records: list[dict],
) -> int | None:
    """Latest year of ANY deed event (arms-length or not). Used for the
    primary tenure cohort bucket since 'last transfer' is what a viewer
    naturally reads from a map legend.
    """
    years: list[int] = []
    for s in sales_records:
        d = s.get("sale_date")
        if d and len(str(d)) >= 4:
            try:
                years.append(int(str(d)[:4]))
            except ValueError:
                pass
    seen: set[tuple] = set()
    for h in hist_records:
        deed_date = h.get("deed_date")
        if not deed_date:
            continue
        key = (str(deed_date)[:10], h.get("deed_book"), h.get("deed_page"))
        if key in seen:
            continue
        seen.add(key)
        try:
            years.append(int(str(deed_date)[:4]))
        except (ValueError, TypeError):
            pass
    return max(years) if years else None


def _latest_arms_length_year(
    sales_records: list[dict],
    hist_records: list[dict],
) -> int | None:
    """Find the year of the most recent arms-length sale across both SR1A
    (sales_history) and Bloustein (modiv_history) deed events.

    Bloustein hist `sale_*` columns are per-parcel-frozen (carry forward),
    so unique deed events are deduped by (deed_date, deed_book, deed_page).
    """
    years: list[int] = []
    for s in sales_records:
        if _is_arms_length(s.get("nu_code")):
            d = s.get("sale_date")
            if d and len(str(d)) >= 4:
                try:
                    years.append(int(str(d)[:4]))
                except ValueError:
                    pass
    seen_deeds: set[tuple] = set()
    for h in hist_records:
        deed_date = h.get("deed_date")
        if not deed_date:
            continue
        # Need actual sale price > 0 to count as a deed event we can attribute
        sp = h.get("sale_price")
        if sp is None:
            continue
        try:
            sp_n = float(sp)
        except (TypeError, ValueError):
            continue
        # Deed events with sale_price=1 are family transfers / token amounts
        # — they have an NU code that excludes them. Carry forward each unique
        # deed_date once.
        key = (str(deed_date)[:10], h.get("deed_book"), h.get("deed_page"))
        if key in seen_deeds:
            continue
        seen_deeds.add(key)
        if not _is_arms_length(h.get("sale_nu_code")):
            continue
        # Only count if there's a meaningful price (> $1000) — guards against
        # nominal-consideration deeds that slipped through with blank NU.
        if sp_n < 1000:
            continue
        try:
            years.append(int(str(deed_date)[:4]))
        except (ValueError, TypeError):
            pass
    return max(years) if years else None


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
            "unified_sales": _build_unified_sales(sales_records, hist_records),
            "data_quality_flags": dq.get(pin, []),
            "cohort": _cohort_tags(
                _latest_arms_length_year(sales_records, hist_records),
                _latest_any_deed_year(sales_records, hist_records),
            ),
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

    # ----- Town aggregates: cohort breakdown of count + tax pool -----
    AGG_OUT = ROOT / "viz" / "src" / "data" / "town_aggregates.json"
    cohort_count: dict[str, int] = defaultdict(int)
    cohort_tax: dict[str, float] = defaultdict(float)
    cohort_assessed: dict[str, float] = defaultdict(float)
    total_tax = 0.0
    total_assessed = 0.0
    parcels_with_tax = 0
    for pin, rec in out.items():
        c = rec.get("cohort", {}).get("cohort", "unknown")
        cohort_count[c] += 1
        ca = rec.get("current_assessment") or {}
        t = ca.get("last_year_tax")
        a = ca.get("net_value")
        try:
            tn = float(t) if t is not None else 0.0
        except (TypeError, ValueError):
            tn = 0.0
        try:
            an = float(a) if a is not None else 0.0
        except (TypeError, ValueError):
            an = 0.0
        if tn > 0:
            cohort_tax[c] += tn
            total_tax += tn
            parcels_with_tax += 1
        if an > 0:
            cohort_assessed[c] += an
            total_assessed += an

    cohort_breakdown = []
    for c in [
        "no_deed_since_1989",
        "tenure_pre_2015",
        "tenure_2015_2019",
        "tenure_pandemic_2020_2022",
        "tenure_post_pandemic_2023plus",
    ]:
        n = cohort_count[c]
        tax = cohort_tax[c]
        assessed = cohort_assessed[c]
        cohort_breakdown.append({
            "cohort": c,
            "n_parcels": n,
            "pct_of_parcels": (100 * n / len(out)) if len(out) else 0,
            "sum_tax": tax,
            "pct_of_tax_pool": (100 * tax / total_tax) if total_tax else 0,
            "sum_assessed": assessed,
            "pct_of_assessed": (100 * assessed / total_assessed) if total_assessed else 0,
            "avg_tax_per_parcel": (tax / n) if n else 0,
            "avg_assessed_per_parcel": (assessed / n) if n else 0,
        })

    aggregates = {
        "total_parcels": len(out),
        "parcels_with_tax_data": parcels_with_tax,
        "total_tax_pool": total_tax,
        "total_assessed_value": total_assessed,
        "cohorts": cohort_breakdown,
    }
    AGG_OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp_agg = AGG_OUT.with_suffix(AGG_OUT.suffix + ".tmp")
    with open(tmp_agg, "w") as f:
        json.dump(aggregates, f, indent=2)
    tmp_agg.replace(AGG_OUT)
    print(f"wrote town aggregates to {AGG_OUT}")
    print(f"   total tax pool: ${total_tax:,.0f}  across {parcels_with_tax} parcels")
    return 0


if __name__ == "__main__":
    sys.exit(main())
