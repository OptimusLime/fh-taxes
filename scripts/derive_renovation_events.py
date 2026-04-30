"""Derive renovation events from existing data via four triangulating signals.

Signal 1 — Annual improvement-value step-up (MAD-based):
  YoY change in improvement_value, residualized against town-year median
  using MAD (robust to reval years). Flag non-sale years where the parcel
  moved >= 1.5 MADs above its year's median AND in absolute terms moved
  at least +10% AND +$25K. Lower threshold than v0 to catch partial
  renovations (kitchen/bath remodels, additions) that don't move the
  whole improvement_value massively.

Signal 1b — 3-year cumulative step-up:
  Sum of pct_imp over a rolling 3-year window without a sale event in any
  of those years. Flags slow-burn renovations where the assessor catches
  up over multiple cycles. Threshold: cumulative >= 30% AND total dollar
  delta over the window >= $75K. Year recorded = the LAST year of the
  window (when the cumulative first crosses threshold).

Signal 2 — Effective-age compression:
  prc.eff_age vs prc.notice_year - prc.year_built. The assessor's own
  estimate of "effective" build year (eff_reno_year = notice_year - eff_age)
  encodes their judgment of renovation. Flag parcels where:
    EITHER reno_gap >= 25 AND eff_age <= 35  (broad: catches partial reno)
    OR     reno_gap >= 40 AND eff_age <= 20  (strict: gut/rebuild)
  We weight the strict variant higher.

Signal 3 — Building-description change:
  modiv_history.building_description string transitions per parcel.
  Flag any (pin, year) where the description string changes vs the prior
  year, EXCLUDING town-wide recoding events (a year where >25% of parcels
  see a description change). Catches: garage added, story added, deck
  added, etc.

Confidence score = weighted sum of signals present:
  - Signal 1  (annual step-up):       +2.0
  - Signal 1b (3-year cumulative):    +1.5
  - Signal 2  (eff_age strict gut):   +1.5
  - Signal 2  (eff_age broad partial):+0.75
  - Signal 3  (desc change):          +1.0

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
    # Arms-length sale events suppress step_up (the assessor's re-pin to
    # sale-price IS the explanation). Family/exempt transfers (NU codes 1,
    # 3, 4, 7, 26, etc.) do NOT — assessor has no clean market anchor for
    # those, so a step-up around a family transfer is more likely real
    # renovation than a price-driven re-pin.
    nu = mh["sale_nu_code"].astype(str).str.strip()
    is_arms = nu.isin(["", "00", "0", "nan", "None"]) | mh["sale_nu_code"].isna()
    mh["sale_event"] = (
        mh["sale_price"].notna()
        & (mh["sale_price"] != mh["prev_sale_price"])
        & is_arms
    )

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

    # No post-2014 floor: the MAD residualization already controls for
    # town-wide reval-year shocks (e.g., 2003 reval), so a parcel that's
    # still far above its year's median is real signal even pre-ADP.
    sig1_mask = (
        (~mh["sale_event"])
        & (mh["pct_imp"] >= 0.10)
        & (mh["delta_imp"] >= 25_000)
        & (mh["mad_z"] >= 1.5)
    )
    sig1 = mh.loc[sig1_mask, ["parcel_pin", "year", "prop_loc", "prev_imp",
                              "improvement_value", "delta_imp", "pct_imp", "mad_z"]].copy()
    sig1["signal"] = "step_up"
    sig1["weight"] = 2.0

    print(f"Signal 1 (annual improvement step-up): {len(sig1)} events across "
          f"{sig1['parcel_pin'].nunique()} parcels")

    # --- Signal 1b: 3-year cumulative step-up (no sale in window) ---
    # For each parcel, slide a 3-year window. If sum(pct_imp) over window >= 30%
    # AND sum(delta_imp) >= $75K AND no sale_event in window, flag the END year.
    # Rolling done per parcel via groupby + apply.
    def cum_flags(g: pd.DataFrame) -> pd.DataFrame:
        g = g.sort_values("year").reset_index(drop=True)
        out_idx = []
        for i in range(2, len(g)):
            window = g.iloc[i - 2 : i + 1]
            if window["sale_event"].any():
                continue
            cum_pct = window["pct_imp"].sum(skipna=True)
            cum_delta = window["delta_imp"].sum(skipna=True)
            if cum_pct >= 0.30 and cum_delta >= 75_000:
                out_idx.append(g.index[i])
        return g.loc[out_idx]

    sig1b_rows = (
        mh.groupby("parcel_pin", group_keys=False)
        [["parcel_pin", "year", "prop_loc", "improvement_value", "delta_imp",
          "pct_imp", "sale_event"]]
        .apply(cum_flags)
    )
    sig1b = sig1b_rows.copy()
    if len(sig1b):
        # Recompute window-summed delta/pct for the event payload
        cum_deltas = []
        cum_pcts = []
        for _, row in sig1b.iterrows():
            pin = row["parcel_pin"]
            yr = row["year"]
            window = mh[(mh["parcel_pin"] == pin) & (mh["year"].between(yr - 2, yr))]
            cum_deltas.append(float(window["delta_imp"].sum(skipna=True)))
            cum_pcts.append(float(window["pct_imp"].sum(skipna=True)))
        sig1b["cum_delta_imp"] = cum_deltas
        sig1b["cum_pct_imp"] = cum_pcts
        sig1b = sig1b[["parcel_pin", "year", "prop_loc", "cum_delta_imp", "cum_pct_imp"]]
    else:
        sig1b = pd.DataFrame(columns=["parcel_pin", "year", "prop_loc",
                                       "cum_delta_imp", "cum_pct_imp"])
    sig1b["signal"] = "cum_step_up"
    sig1b["weight"] = 1.5
    # Avoid double-counting parcels that already have an annual step_up at the
    # same year (the annual event subsumes the cumulative for that year).
    if len(sig1) and len(sig1b):
        annual_keys = set(zip(sig1["parcel_pin"], sig1["year"]))
        sig1b = sig1b[~sig1b.apply(
            lambda r: (r["parcel_pin"], r["year"]) in annual_keys, axis=1
        )]
    print(f"Signal 1b (3-yr cumulative step-up): {len(sig1b)} events across "
          f"{sig1b['parcel_pin'].nunique() if len(sig1b) else 0} parcels")

    # --- Signal 2: effective-age compression (two tiers) ---
    prc = pd.read_parquet(PROC / "prc.parquet")
    prc["eff_reno_year"] = prc["notice_year"] - prc["eff_age"]
    prc["reno_gap"] = prc["eff_reno_year"] - prc["year_built"]
    base = prc[prc["reno_gap"].notna() & prc["eff_age"].notna()].copy()
    # Strict: gut/teardown re-baseline
    strict_mask = (base["reno_gap"] >= 40) & (base["eff_age"] <= 20)
    sig2_strict = base.loc[strict_mask, ["pams_pin", "prop_loc", "year_built",
                                          "eff_age", "notice_year",
                                          "eff_reno_year", "reno_gap"]].copy()
    sig2_strict = sig2_strict.rename(columns={"pams_pin": "parcel_pin",
                                              "eff_reno_year": "year"})
    sig2_strict["signal"] = "eff_age"
    sig2_strict["weight"] = 1.5
    # Broad: partial reno / kitchen+bath / addition
    broad_mask = (
        ((base["reno_gap"] >= 25) & (base["eff_age"] <= 35))
        & ~strict_mask
    )
    sig2_broad = base.loc[broad_mask, ["pams_pin", "prop_loc", "year_built",
                                        "eff_age", "notice_year",
                                        "eff_reno_year", "reno_gap"]].copy()
    sig2_broad = sig2_broad.rename(columns={"pams_pin": "parcel_pin",
                                            "eff_reno_year": "year"})
    sig2_broad["signal"] = "eff_age_partial"
    sig2_broad["weight"] = 0.75
    sig2 = pd.concat([sig2_strict, sig2_broad], ignore_index=True)

    print(f"Signal 2 strict (eff_age gut, gap>=40 & eff_age<=20):  "
          f"{len(sig2_strict)} parcels")
    print(f"Signal 2 broad  (eff_age partial, gap>=25 & eff_age<=35): "
          f"{len(sig2_broad)} parcels")

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

    # --- Signal 4: year_built changed forward in modiv_history ---
    # When the assessor revises year_built FORWARD by 10+ years mid-history,
    # they have explicitly recoded the build vintage — usually after a
    # gut/rebuild walk-through. Excluded if either side is NaN (initial
    # population events) or the change is backward (historical correction).
    mh["yb_num"] = pd.to_numeric(mh["year_built"], errors="coerce")
    mh["prev_yb"] = mh.groupby("parcel_pin")["yb_num"].shift(1)
    yb_jump = (
        mh["prev_yb"].notna()
        & mh["yb_num"].notna()
        & ((mh["yb_num"] - mh["prev_yb"]) >= 10)
    )
    sig4 = mh.loc[yb_jump, ["parcel_pin", "year", "prop_loc", "prev_yb",
                            "yb_num"]].copy()
    sig4 = sig4.rename(columns={"prev_yb": "old_year_built", "yb_num": "new_year_built"})
    sig4["signal"] = "year_built_change"
    sig4["weight"] = 1.5
    print(f"Signal 4 (year_built forward jump >=10): {len(sig4)} events across "
          f"{sig4['parcel_pin'].nunique() if len(sig4) else 0} parcels")

    # --- Combine into events log ---
    events_cols = ["parcel_pin", "year", "prop_loc", "signal", "weight"]
    parts = [sig1[events_cols + ["delta_imp", "pct_imp", "mad_z"]]]
    if len(sig1b):
        parts.append(sig1b[events_cols + ["cum_delta_imp", "cum_pct_imp"]])
    parts.append(sig2[events_cols + ["reno_gap", "eff_age"]])
    parts.append(sig3[events_cols + ["prev_desc", "building_description"]])
    if len(sig4):
        parts.append(sig4[events_cols + ["old_year_built", "new_year_built"]])
    events = pd.concat(parts, ignore_index=True)
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
    # Tier classification — updated to handle 5 signal types.
    # Strong = step_up (annual or cumulative) OR eff_age (strict).
    # Soft   = eff_age_partial OR desc_change.
    def tier(row: pd.Series) -> str:
        c = row["confidence"]
        sigs = set(row["signals"])
        strong = sigs & {"step_up", "cum_step_up", "eff_age", "year_built_change"}
        if c >= 4.5 or len(strong) >= 2:
            return "high"
        if c >= 2.5 or strong:
            return "medium"
        if c >= 1.0:
            return "low"
        return "weak"

    summary["tier"] = summary.apply(tier, axis=1)
    summary.to_parquet(PROC / "renovation_summary.parquet", index=False)

    print("\nTier distribution:")
    print(summary["tier"].value_counts().to_string())
    print(f"\nTotal flagged parcels: {len(summary)} / {len(prc)} ({len(summary)/len(prc)*100:.1f}%)")

    # --- Per-parcel JSON overlay ---
    # Drop tier="weak" parcels (only soft signals fired, e.g., partial eff_age
    # alone). They are recorded in the parquet but not exposed in the drawer
    # overlay — too low confidence to assert as a "suspected renovation."
    OVERLAYS.mkdir(parents=True, exist_ok=True)
    weak_pins = set(summary[summary["tier"] == "weak"]["parcel_pin"])
    overlay: dict[str, dict] = {}
    for pin, grp in events.groupby("parcel_pin"):
        if pin in weak_pins:
            continue
        evts = []
        for _, e in grp.iterrows():
            ev: dict = {"signal": e["signal"], "weight": float(e["weight"])}
            if pd.notna(e["year"]):
                ev["year"] = int(e["year"])
            for k in ("delta_imp", "pct_imp", "mad_z", "cum_delta_imp", "cum_pct_imp", "reno_gap", "eff_age", "old_year_built", "new_year_built"):
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
    for needle, pin in [
        ("93 BATTIN", "1314_79_3"),
        ("144 BUTTONWOOD", "1314_76_2"),
        ("25 FAIR HAVEN", "1314_47_3"),
    ]:
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
