"""Derive renovation events from existing data via three triangulating signals.

Signal 1 — Improvement-value step-up (MAD-based):
  YoY change in improvement_value, residualized against town-year median
  using MAD (robust to reval years). Flag non-sale years where the parcel
  moved >= 3 MADs above its year's median AND in absolute terms moved at
  least +20% AND +$50K.

Signal 2 — Effective-age compression:
  prc.eff_age vs prc.notice_year - prc.year_built. The assessor's own
  estimate of "effective" build year (eff_reno_year = notice_year - eff_age)
  encodes their judgment of renovation. Flag parcels where:
    eff_reno_year - year_built >= 40 (top quartile gap)
    AND eff_age <= 20 (recent perceived freshness)
  This catches gut renovations / teardowns that the assessor has
  re-baselined.

Signal 3 — Building-description change:
  modiv_history.building_description string transitions per parcel.
  Flag any (pin, year) where the description string changes vs the prior
  year, EXCLUDING town-wide recoding events (e.g., 2003 when nearly every
  parcel switched from old format `1SF2G1AB` to new format `1S-F-R-AG-1U`).
  A recoding year is one where >25% of parcels see a description change.

Confidence score = weighted sum of signals present:
  - Signal 1 (step-up): +2 (most direct evidence of work being done)
  - Signal 2 (eff_age compression): +1.5 (assessor's own conclusion)
  - Signal 3 (desc change, non-recoding year): +1 (suggestive)

Outputs:
  data/processed/renovation_events.parquet  — per-(pin, year) event log
  data/processed/renovation_summary.parquet — per-pin summary (best signal)
  viz/src/data/overlays/renovations.json    — pin -> { events, score, summary }

Usage:
  python scripts/derive_renovation_events.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OVERLAYS = ROOT / "viz" / "src" / "data" / "overlays"


def main() -> None:
    mh = pd.read_parquet(PROC / "modiv_history.parquet")
    mh = mh.sort_values(["parcel_pin", "year"]).reset_index(drop=True)
    mh["improvement_value"] = pd.to_numeric(mh["improvement_value"], errors="coerce")
    mh["sale_price"] = pd.to_numeric(mh["sale_price"], errors="coerce")
    mh["prev_imp"] = mh.groupby("parcel_pin")["improvement_value"].shift(1)
    mh["delta_imp"] = mh["improvement_value"] - mh["prev_imp"]
    mh["pct_imp"] = mh["delta_imp"] / mh["prev_imp"]
    mh["prev_sale_price"] = mh.groupby("parcel_pin")["sale_price"].shift(1)
    mh["sale_event"] = mh["sale_price"].notna() & (mh["sale_price"] != mh["prev_sale_price"])

    # --- Signal 1: MAD-based step-up vs town-year baseline ---
    # MAD is robust to reval-year shocks where mean/std blow up.
    finite = mh["pct_imp"].replace([np.inf, -np.inf], np.nan).notna()
    non_sale = mh[(~mh["sale_event"]) & finite]

    def mad(x: pd.Series) -> float:
        m = x.median()
        return float((x - m).abs().median())

    year_stats = (
        non_sale.groupby("year")["pct_imp"]
        .agg(yr_median="median", yr_mad=mad, yr_n="count")
        .reset_index()
    )
    mh = mh.merge(year_stats, on="year", how="left")
    # Robust z-score using 1.4826 * MAD as std-equivalent
    mh["mad_z"] = (mh["pct_imp"] - mh["yr_median"]) / (1.4826 * mh["yr_mad"].replace(0, np.nan))

    sig1_mask = (
        (~mh["sale_event"])
        & (mh["pct_imp"] >= 0.20)
        & (mh["delta_imp"] >= 50_000)
        & (mh["mad_z"] >= 3.0)
        & (mh["year"] >= 2014)
    )
    sig1 = mh.loc[sig1_mask, ["parcel_pin", "year", "prop_loc", "prev_imp",
                              "improvement_value", "delta_imp", "pct_imp", "mad_z"]].copy()
    sig1["signal"] = "step_up"
    sig1["weight"] = 2.0

    print(f"Signal 1 (improvement step-up): {len(sig1)} events across "
          f"{sig1['parcel_pin'].nunique()} parcels")

    # --- Signal 2: effective-age compression ---
    prc = pd.read_parquet(PROC / "prc.parquet")
    prc["eff_reno_year"] = prc["notice_year"] - prc["eff_age"]
    prc["reno_gap"] = prc["eff_reno_year"] - prc["year_built"]
    sig2_mask = (
        prc["reno_gap"].notna()
        & (prc["reno_gap"] >= 40)
        & (prc["eff_age"].notna())
        & (prc["eff_age"] <= 20)
    )
    sig2 = prc.loc[sig2_mask, ["pams_pin", "prop_loc", "year_built", "eff_age",
                                "notice_year", "eff_reno_year", "reno_gap"]].copy()
    sig2 = sig2.rename(columns={"pams_pin": "parcel_pin", "eff_reno_year": "year"})
    sig2["signal"] = "eff_age"
    sig2["weight"] = 1.5

    print(f"Signal 2 (effective-age compression): {len(sig2)} parcels with "
          f"reno_gap>=40 and eff_age<=20")

    # --- Signal 3: building-description change ---
    mh["prev_desc"] = mh.groupby("parcel_pin")["building_description"].shift(1)
    mh["desc_changed"] = (
        mh["prev_desc"].notna()
        & mh["building_description"].notna()
        & (mh["prev_desc"] != mh["building_description"])
    )
    # Town-wide recoding years: drop years where >25% of parcels changed desc
    desc_year_pct = mh.groupby("year")["desc_changed"].mean()
    recoding_years = set(desc_year_pct[desc_year_pct > 0.25].index.tolist())
    print(f"Town-wide recoding years (excluded from signal 3): {sorted(recoding_years)}")

    sig3_mask = mh["desc_changed"] & ~mh["year"].isin(recoding_years)
    sig3 = mh.loc[sig3_mask, ["parcel_pin", "year", "prop_loc", "prev_desc",
                              "building_description"]].copy()
    sig3["signal"] = "desc_change"
    sig3["weight"] = 1.0

    print(f"Signal 3 (description change, non-recoding): {len(sig3)} events across "
          f"{sig3['parcel_pin'].nunique()} parcels")

    # --- Combine into events log ---
    events_cols = ["parcel_pin", "year", "prop_loc", "signal", "weight"]
    events = pd.concat(
        [sig1[events_cols + ["delta_imp", "pct_imp", "mad_z"]],
         sig2[events_cols + ["reno_gap", "eff_age"]],
         sig3[events_cols + ["prev_desc", "building_description"]]],
        ignore_index=True,
    )
    events["year"] = events["year"].astype("Int64")
    events = events.sort_values(["parcel_pin", "year", "weight"], ascending=[True, True, False])

    PROC.mkdir(parents=True, exist_ok=True)
    events.to_parquet(PROC / "renovation_events.parquet", index=False)
    print(f"\nWrote {len(events)} events → {PROC / 'renovation_events.parquet'}")

    # --- Per-parcel summary ---
    summary = (
        events.groupby("parcel_pin")
        .agg(
            n_events=("signal", "count"),
            confidence=("weight", "sum"),
            signals=("signal", lambda s: sorted(set(s))),
            first_event_year=("year", "min"),
            last_event_year=("year", "max"),
        )
        .reset_index()
    )
    # Tier classification
    def tier(row: pd.Series) -> str:
        c = row["confidence"]
        sigs = set(row["signals"])
        if c >= 4.5 or {"step_up", "eff_age", "desc_change"}.issubset(sigs):
            return "high"
        if c >= 2.5 or {"step_up", "eff_age"}.issubset(sigs):
            return "medium"
        if c >= 1.5:
            return "low"
        return "weak"

    summary["tier"] = summary.apply(tier, axis=1)
    summary.to_parquet(PROC / "renovation_summary.parquet", index=False)

    print("\nTier distribution:")
    print(summary["tier"].value_counts().to_string())
    print(f"\nTotal flagged parcels: {len(summary)} / {len(prc)} ({len(summary)/len(prc)*100:.1f}%)")

    # --- Per-parcel JSON overlay ---
    OVERLAYS.mkdir(parents=True, exist_ok=True)
    overlay: dict[str, dict] = {}
    for pin, grp in events.groupby("parcel_pin"):
        evts = []
        for _, e in grp.iterrows():
            ev: dict = {"signal": e["signal"], "weight": float(e["weight"])}
            if pd.notna(e["year"]):
                ev["year"] = int(e["year"])
            for k in ("delta_imp", "pct_imp", "mad_z", "reno_gap", "eff_age"):
                v = e.get(k)
                if pd.notna(v):
                    ev[k] = float(v)
            for k in ("prev_desc", "building_description"):
                v = e.get(k)
                if isinstance(v, str) and v:
                    ev[k] = v
            evts.append(ev)
        s = summary[summary["parcel_pin"] == pin].iloc[0]
        overlay[pin] = {
            "tier": s["tier"],
            "confidence": float(s["confidence"]),
            "signals": list(s["signals"]),
            "first_event_year": int(s["first_event_year"]) if pd.notna(s["first_event_year"]) else None,
            "last_event_year": int(s["last_event_year"]) if pd.notna(s["last_event_year"]) else None,
            "events": evts,
        }

    out = OVERLAYS / "renovations.json"
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(overlay, indent=2, default=str))
    tmp.replace(out)
    print(f"\nWrote overlay → {out} ({len(overlay)} parcels)")

    # --- Probe: user's named parcels ---
    print("\n=== User-named probe parcels ===")
    for needle, pin in [("93 BATTIN", "1314_79_3"), ("144 BUTTONWOOD", "1314_76_2")]:
        if pin in overlay:
            o = overlay[pin]
            print(f"\n{needle} ({pin}): tier={o['tier']}, confidence={o['confidence']}, "
                  f"signals={o['signals']}")
            for e in o["events"]:
                print(f"  - {e}")
        else:
            print(f"\n{needle} ({pin}): NOT flagged.")


if __name__ == "__main__":
    main()
