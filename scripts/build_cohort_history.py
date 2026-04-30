"""Cohort history time series — annual assessed-value distribution by tenure.

Each parcel is assigned its CURRENT cohort (based on latest deed event, same
logic as build_parcels_full_data.py). Then for each year y in modiv_history
(1989-2025), we compute per cohort:

  - n_parcels in that year (parcels that existed in modiv that year)
  - sum_assessed (net_value)
  - avg_assessed
  - share_of_total_assessed  (cohort_assessed / town_assessed)
  - share_of_total_parcels    (cohort_n / town_n)

These two shares yield a defensible descriptive narrative for the
TownComposition page:

  "If parcels were equal-value, share_of_assessed would equal
   share_of_parcels. The gap is the assessor's record of how much
   above/below head-count each cohort sits, year by year. We do NOT
   yet claim the gap is correct or incorrect — Plan 4 (hedonic) tests
   that. What we CAN show is the trajectory: how each cohort's share
   has moved over time."

Cumulative-dollar framing (clearly labeled as descriptive):

  For each year y: implied_dollar_position_c,y =
      (share_of_assessed_c,y - share_of_parcels_c,y) * implied_levy_y

  implied_levy_y = total_assessed_y * current_effective_rate
                   (current 2025 effective rate ≈ 1.352%)

  cumulative position = sum over y of implied_dollar_position.

  POSITIVE => cohort's parcels carried a larger assessed-value share
  than their head-count share (paid more than equal-split parity).
  NEGATIVE => carried less.

  Important caveat: parity-with-head-count is NOT a fair-share baseline
  because houses differ in size/quality. The hedonic in Plan 4 produces
  a true fair-share number; this is a descriptive floor that's honest
  about its assumption.

Outputs:
  viz/src/data/cohort_history.json — time series consumed by the page

Reproducible from data/processed/* (no manual steps).
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "viz" / "src" / "data" / "cohort_history.json"

# Cohort assignment (mirrors build_parcels_full_data.py:_cohort_tags).
ARMS_LENGTH_NU = {None, "", "00", "0"}


def _cohort_for(latest_arms: int | None, latest_any: int | None) -> str:
    bucket = latest_any
    if bucket is None:
        return "no_deed_since_1989"
    if bucket < 2015:
        return "tenure_pre_2015"
    if bucket < 2020:
        return "tenure_2015_2019"
    if bucket < 2023:
        return "tenure_pandemic_2020_2022"
    return "tenure_post_pandemic_2023plus"


def main() -> None:
    mh = pd.read_parquet(PROC / "modiv_history.parquet")
    mh["net_value"] = pd.to_numeric(mh["net_value"], errors="coerce")
    mh["sale_price"] = pd.to_numeric(mh["sale_price"], errors="coerce")

    # Per-parcel: derive latest-arms-length and latest-any-deed years from history.
    # Latest-any-deed = latest year with non-null deed_book/deed_page or sale_price.
    # Latest-arms = latest year above with NU code in arms-length set.
    mh["has_deed"] = mh["deed_book"].notna() | mh["deed_page"].notna() | mh["sale_price"].notna()
    is_arms = mh["sale_nu_code"].isna() | mh["sale_nu_code"].astype(str).str.strip().isin(["", "00", "0"])
    mh["arms_event"] = mh["has_deed"] & is_arms

    latest_any = (
        mh[mh["has_deed"]].groupby("parcel_pin")["year"].max()
    )
    latest_arms = (
        mh[mh["arms_event"]].groupby("parcel_pin")["year"].max()
    )
    cohort_by_pin: dict[str, str] = {}
    all_pins = mh["parcel_pin"].unique()
    for pin in all_pins:
        cohort_by_pin[pin] = _cohort_for(
            int(latest_arms[pin]) if pin in latest_arms else None,
            int(latest_any[pin]) if pin in latest_any else None,
        )

    # Year-by-year aggregation
    mh["cohort"] = mh["parcel_pin"].map(cohort_by_pin)
    mh = mh[mh["net_value"].notna() & (mh["net_value"] > 0)]

    cohorts_order = [
        "no_deed_since_1989",
        "tenure_pre_2015",
        "tenure_2015_2019",
        "tenure_pandemic_2020_2022",
        "tenure_post_pandemic_2023plus",
    ]

    # Current effective rate from 2025 totals; used as the implied-levy multiplier
    # for prior years. Documented in the page as a descriptive simplification.
    last_year = int(mh["year"].max())
    last = mh[mh["year"] == last_year]
    cur_eff_rate = float(
        # We approximate: total levy ≈ total assessed × rate, where rate is
        # taken from constants.TAX_RATE_PER_HUNDRED ($1.427 / $100 = 1.427%).
        # Avoids importing constants module.
        0.01427
    )

    series = []
    for y in sorted(mh["year"].unique()):
        sub = mh[mh["year"] == y]
        total_a = float(sub["net_value"].sum())
        total_n = int(len(sub))
        implied_levy = total_a * cur_eff_rate
        per_cohort = []
        for c in cohorts_order:
            csub = sub[sub["cohort"] == c]
            n = int(len(csub))
            a = float(csub["net_value"].sum())
            share_a = (a / total_a) if total_a else 0.0
            share_n = (n / total_n) if total_n else 0.0
            implied_pos = (share_a - share_n) * implied_levy
            per_cohort.append({
                "cohort": c,
                "n_parcels": n,
                "sum_assessed": a,
                "avg_assessed": (a / n) if n else 0.0,
                "share_of_assessed": share_a,
                "share_of_parcels": share_n,
                "implied_dollar_position": implied_pos,
            })
        series.append({
            "year": int(y),
            "total_assessed": total_a,
            "total_parcels": total_n,
            "implied_levy": implied_levy,
            "cohorts": per_cohort,
        })

    # Cumulative position per cohort, ADP-era only (>=2014)
    cumulative_adp: dict[str, float] = defaultdict(float)
    cumulative_full: dict[str, float] = defaultdict(float)
    for row in series:
        for c in row["cohorts"]:
            cumulative_full[c["cohort"]] += c["implied_dollar_position"]
            if row["year"] >= 2014:
                cumulative_adp[c["cohort"]] += c["implied_dollar_position"]

    summary = {
        "current_effective_rate": cur_eff_rate,
        "year_min": int(mh["year"].min()),
        "year_max": last_year,
        "adp_start": 2014,
        "cumulative_position_full_history": [
            {"cohort": c, "dollars": cumulative_full[c]} for c in cohorts_order
        ],
        "cumulative_position_adp_era": [
            {"cohort": c, "dollars": cumulative_adp[c]} for c in cohorts_order
        ],
    }

    out = {"summary": summary, "annual": series}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(out, indent=2, default=float))
    tmp.replace(OUT)

    print(f"Wrote {len(series)} years × {len(cohorts_order)} cohorts → {OUT}")
    print("\nADP-era cumulative position (sum of share_assessed - share_parcels × implied_levy):")
    for c in cohorts_order:
        d = cumulative_adp[c]
        sign = "+" if d > 0 else ""
        print(f"  {c:35s} {sign}${d/1e6:>8.2f}M")
    print("\nIf the assessor's records are accurate, these numbers describe how each")
    print("cohort's share-of-assessed has tracked vs share-of-parcels — they are NOT yet")
    print("a fair-share verdict. Plan 4 (hedonic) controls for size/age/quality.")


if __name__ == "__main__":
    main()
