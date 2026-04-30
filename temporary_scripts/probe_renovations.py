"""Renovation-event probe.

Methodology (v0):
  For each (parcel, year) compute YoY % change in improvement_value.
  Flag the row as a renovation candidate if:
    - non-sale year (no deed/sale_price recorded that year)
    - improvement_value increased at least +20% AND at least +$50K
    - z-score of that pct change vs town-wide *non-sale* changes for that
      same year >= 2.0 (controls for reassessment/recoding years like 2003,
      2014, 2024 where the whole town moves together)

Why town-year normalization: the 2003 and 2014 reval years move every
parcel by 30-60% in lockstep — those are not renovations, those are
re-baselining. By comparing each parcel against the median move *for its
year*, we isolate idiosyncratic step-ups.

Outputs to stdout: top 20 renovation candidates by z-score, plus the
specific parcels the user named (93 BATTIN, 144 BUTTONWOOD).
"""
from __future__ import annotations

import pandas as pd
import numpy as np

mh = pd.read_parquet("data/processed/modiv_history.parquet")
mh = mh.sort_values(["parcel_pin", "year"]).reset_index(drop=True)

# Numeric coercion
mh["improvement_value"] = pd.to_numeric(mh["improvement_value"], errors="coerce")
mh["sale_price"] = pd.to_numeric(mh["sale_price"], errors="coerce")

# Per-parcel YoY change
mh["prev_imp"] = mh.groupby("parcel_pin")["improvement_value"].shift(1)
mh["delta_imp"] = mh["improvement_value"] - mh["prev_imp"]
mh["pct_imp"] = mh["delta_imp"] / mh["prev_imp"]

# Flag sale-bearing rows: deed_date or sale_price changed vs prior row
mh["prev_sale_price"] = mh.groupby("parcel_pin")["sale_price"].shift(1)
mh["sale_event"] = (mh["sale_price"].notna()) & (mh["sale_price"] != mh["prev_sale_price"])

# Town-wide stats by year on NON-SALE rows
non_sale = mh[(~mh["sale_event"]) & mh["pct_imp"].notna() & np.isfinite(mh["pct_imp"])]
year_stats = non_sale.groupby("year")["pct_imp"].agg(["median", "std", "count"]).reset_index()
year_stats = year_stats.rename(columns={"median": "yr_median", "std": "yr_std", "count": "yr_n"})

mh = mh.merge(year_stats, on="year", how="left")
mh["zscore"] = (mh["pct_imp"] - mh["yr_median"]) / mh["yr_std"]

# Renovation candidates
cand = mh[
    (~mh["sale_event"])
    & (mh["pct_imp"] >= 0.20)
    & (mh["delta_imp"] >= 50_000)
    & (mh["zscore"] >= 2.0)
    & (mh["year"] >= 2014)  # ADP era — pre-2014 data has decadal reval shocks
].copy()

print(f"\n=== Renovation candidates (post-ADP, z>=2, +20%/+$50K, non-sale): {len(cand)} ===")
print(f"Across {cand['parcel_pin'].nunique()} unique parcels.")
print()

# Top 20 by zscore
top = cand.sort_values("zscore", ascending=False).head(20)
print("--- Top 20 by z-score ---")
cols = ["parcel_pin", "year", "prop_loc", "prev_imp", "improvement_value", "delta_imp", "pct_imp", "zscore"]
fmt = top[cols].copy()
fmt["pct_imp"] = (fmt["pct_imp"] * 100).round(1).astype(str) + "%"
fmt["zscore"] = fmt["zscore"].round(2)
fmt["prev_imp"] = fmt["prev_imp"].astype("Int64")
fmt["improvement_value"] = fmt["improvement_value"].astype("Int64")
fmt["delta_imp"] = fmt["delta_imp"].astype("Int64")
print(fmt.to_string(index=False))

# User's named parcels
print("\n--- User-named probe parcels ---")
for needle in ["93 BATTIN", "144 BUTTONWOOD"]:
    pin = mh[mh["prop_loc"].str.contains(needle, case=False, na=False)]["parcel_pin"].iloc[0]
    sub = mh[(mh["parcel_pin"] == pin) & (mh["year"] >= 2014)][
        ["year", "improvement_value", "delta_imp", "pct_imp", "zscore", "sale_event"]
    ].copy()
    sub["pct_imp"] = (sub["pct_imp"] * 100).round(1).astype(str) + "%"
    sub["zscore"] = sub["zscore"].round(2)
    print(f"\n{needle} ({pin}):")
    print(sub.to_string(index=False))
    flagged = cand[cand["parcel_pin"] == pin]
    if len(flagged):
        print(f"  >> Flagged renovation year(s): {sorted(flagged['year'].tolist())}")
    else:
        print("  >> NOT flagged by current heuristic.")

# Distribution by year — sanity check that we're not just catching reval years
print("\n--- Candidate count by year (should NOT cluster on a single year if heuristic works) ---")
print(cand.groupby("year").size().to_string())
