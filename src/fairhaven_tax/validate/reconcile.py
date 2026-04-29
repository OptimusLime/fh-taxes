"""MOD-IV ↔ SR1A last-sale reconciliation (D-18 / D-19).

D-18: last arms-length sale per parcel = MAX(sale_date), tie-break MAX(sale_price).
D-19: emit reconciliation diffs when |sr1a_date - modiv_date| > 180 days OR
      |price_pct_diff| > 5%. NON-BLOCKING (does not affect validation gate).
"""
from __future__ import annotations

from decimal import Decimal

import geopandas as gpd
import pandas as pd

from fairhaven_tax import constants


DIFF_DATE_DAYS = 180
DIFF_PRICE_PCT = constants.VALIDATION_TOLERANCE  # 0.05


def resolve_last_arms_length_sale(sales_df: pd.DataFrame) -> pd.DataFrame:
    """For each parcel_pin: pick MAX(sale_date), tie-break MAX(sale_price).

    Returns DataFrame with columns: parcel_pin, last_sale_date, last_sale_price,
    last_sale_nu_code.
    """
    if sales_df.empty:
        return pd.DataFrame(
            columns=["parcel_pin", "last_sale_date", "last_sale_price", "last_sale_nu_code"]
        )
    # MAX(sale_date) tie-break MAX(sale_price): D-18 explicit rule
    ordered = sales_df.sort_values(
        ["parcel_pin", "sale_date", "sale_price"],
        ascending=[True, False, False],
    )
    resolved = ordered.drop_duplicates("parcel_pin", keep="first").copy()
    out = resolved[["parcel_pin", "sale_date", "sale_price", "nu_code"]].rename(
        columns={
            "sale_date": "last_sale_date",
            "sale_price": "last_sale_price",
            "nu_code": "last_sale_nu_code",
        }
    ).reset_index(drop=True)
    return out


def _to_ts(v) -> pd.Timestamp | None:
    if v is None:
        return None
    if isinstance(v, pd.Timestamp):
        return v
    try:
        ts = pd.Timestamp(v)
        if pd.isna(ts):
            return None
        return ts
    except (ValueError, TypeError):
        return None


def reconcile_last_sale(
    parcels_gdf: gpd.GeoDataFrame, sales_df: pd.DataFrame
) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """Merge SR1A-resolved last sale onto parcels; emit MOD-IV vs SR1A diffs.

    Returns (parcels_with_last_sale, reconciliation_diffs_df).

    Threshold (D-19): row in diffs when |date_diff| > 180 days OR |price_pct_diff| > 5%.
    """
    resolved = resolve_last_arms_length_sale(sales_df)

    # Left join SR1A resolved last-sale onto parcels by pams_pin
    merged = parcels_gdf.merge(
        resolved, how="left", left_on="pams_pin", right_on="parcel_pin"
    )

    # Determine source per row
    sr1a_has = merged["last_sale_date"].notna()
    modiv_has = (
        merged["modiv_last_sale_date"].notna()
        if "modiv_last_sale_date" in merged.columns
        else pd.Series([False] * len(merged))
    )

    # Where SR1A is null but MOD-IV is populated, copy MOD-IV into last_sale_*
    if "modiv_last_sale_date" in merged.columns:
        fb_mask = (~sr1a_has) & modiv_has
        merged.loc[fb_mask, "last_sale_date"] = merged.loc[fb_mask, "modiv_last_sale_date"]
        merged.loc[fb_mask, "last_sale_price"] = merged.loc[fb_mask, "modiv_last_sale_price"]
        merged.loc[fb_mask, "last_sale_nu_code"] = merged.loc[fb_mask, "modiv_last_sale_nu_code"]

    sources = []
    for sr1a_ok, modiv_ok in zip(sr1a_has, modiv_has):
        if sr1a_ok:
            sources.append("sr1a")
        elif modiv_ok:
            sources.append("modiv")
        else:
            sources.append(None)
    merged["last_sale_source"] = sources

    # Drop the helper parcel_pin column from the join
    if "parcel_pin" in merged.columns:
        merged = merged.drop(columns=["parcel_pin"])

    # Build diffs (only when BOTH SR1A and MOD-IV present)
    diff_rows: list[dict] = []
    if "modiv_last_sale_date" in parcels_gdf.columns:
        for _, r in merged.iterrows():
            sr1a_date = r.get("last_sale_date")
            modiv_date = r.get("modiv_last_sale_date")
            sr1a_price = r.get("last_sale_price")
            modiv_price = r.get("modiv_last_sale_price")
            # only compare when both populated AND we have a real SR1A row (not the
            # MOD-IV fallback we just copied in).
            sr1a_real = r.get("last_sale_source") == "sr1a"
            if not sr1a_real:
                continue
            sr1a_ts = _to_ts(sr1a_date)
            modiv_ts = _to_ts(modiv_date)
            if sr1a_ts is None or modiv_ts is None:
                continue
            date_diff_days = abs((sr1a_ts - modiv_ts).days)
            try:
                sp = Decimal(str(sr1a_price)) if sr1a_price is not None else None
                mp = Decimal(str(modiv_price)) if modiv_price is not None else None
            except Exception:
                sp = mp = None
            if sp is None or mp is None or sp == 0 or mp == 0:
                price_pct_diff = Decimal("0")
            else:
                denom = sp if sp > mp else mp
                price_pct_diff = abs(sp - mp) / denom
            if date_diff_days > DIFF_DATE_DAYS or price_pct_diff > DIFF_PRICE_PCT:
                diff_rows.append({
                    "parcel_pin": r.get("pams_pin"),
                    "sr1a_sale_date": sr1a_date,
                    "sr1a_sale_price": sr1a_price,
                    "sr1a_nu_code": r.get("last_sale_nu_code"),
                    "modiv_sale_date": modiv_date,
                    "modiv_sale_price": modiv_price,
                    "modiv_nu_code": r.get("modiv_last_sale_nu_code"),
                    "date_diff_days": int(date_diff_days),
                    "price_pct_diff": float(price_pct_diff),
                })

    diffs_df = pd.DataFrame(diff_rows, columns=[
        "parcel_pin", "sr1a_sale_date", "sr1a_sale_price", "sr1a_nu_code",
        "modiv_sale_date", "modiv_sale_price", "modiv_nu_code",
        "date_diff_days", "price_pct_diff",
    ])

    # Re-wrap as GeoDataFrame to preserve CRS
    out = gpd.GeoDataFrame(merged, geometry="geometry", crs=parcels_gdf.crs)
    return out, diffs_df
