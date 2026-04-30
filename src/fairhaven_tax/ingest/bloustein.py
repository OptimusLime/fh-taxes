"""Load Rutgers Bloustein MOD-IV historical CSVs (1989-2025) → tidy frame keyed (parcel_pin, year).

Bloustein publishes 132-column CSVs per (municipality, year). The full schema is
uniform across 1989-2025 — same 132 columns, same names. This loader reduces
to the D-34 canonical schema (~18 fields) used by Phase 2's CDF gap test and
tax-shift analysis.

OWNER NAME NOTE (deviation from plan D-35):
    Bloustein CSVs do NOT contain owner names. The closest signal is the
    (street_address, city_state) pair which is the OWNER MAILING ADDRESS
    (where tax bills are sent). When city_state ≠ "FAIR HAVEN", that signals
    an out-of-town / absentee owner — useful for tenure / absentee analysis
    but not a personal name. We therefore expose `owner_mailing_address`
    instead of `owner_name`. Daniel's Law (D-35) concerns are reduced — no
    PII names — but mailing addresses still warrant private-use-only
    handling and are stripped before any public artifact (Phase 3).

DATE FORMAT NOTE:
    Despite the column name `deed_date_MMDDYY`, Bloustein actually emits
    ISO `YYYY-MM-DD` strings (verified across 1989, 2020, 2025). The
    suffix is a vestigial naming artifact from the legacy MOD-IV layout.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from fairhaven_tax import constants
from fairhaven_tax.ingest.pams_pin import build_pams_pin


CANONICAL_HISTORY_COLS: list[str] = [
    "parcel_pin",
    "year",
    "owner_mailing_address",
    "prop_loc",
    "land_value",
    "improvement_value",
    "net_value",
    "deductions",
    "deed_book",
    "deed_page",
    "deed_date",
    "sale_price",
    "sale_assessment",
    "sale_nu_code",
    "year_built",
    "building_description",
    "calculated_acreage",
    "num_dwellings",
]


# Map Bloustein raw column → internal staging name. Unmapped columns are
# dropped at projection time. Names prefixed with `_` are intermediate fields
# consumed when constructing parcel_pin / owner_mailing_address.
BLOUSTEIN_TO_CANONICAL: dict[str, str] = {
    "property_id_blk":          "_block",
    "property_id_lot":          "_lot",
    "property_id_qualifier":    "_qualifier",
    "street_address":           "_street_address",
    "city_state":               "_city_state",
    "property_location":        "prop_loc",
    "building_description":     "building_description",
    "land_value":               "land_value",
    "improvement_value":        "improvement_value",
    "net_taxable_value":        "net_value",
    "deduction_amount":         "deductions",
    "deed_book":                "deed_book",
    "deed_page":                "deed_page",
    "deed_date_MMDDYY":         "_deed_date_raw",
    "sale_price":               "sale_price",
    "sale_assessment":          "sale_assessment",
    "sale_sr1a_non_usable_code":"sale_nu_code",
    "year_constructed":         "_year_built_raw",
    "calculated_acreage":       "calculated_acreage",
    "number_of_dwellings":      "_num_dwellings_raw",
    "mun_code_id":              "_mun_code_id",
}


_FILENAME_YEAR_RE = re.compile(r"mod_iv_(\d{4})\.csv$")
_FAIR_HAVEN_MUN_CODE_ID = "234"  # Bloustein's munis_code for Fair Haven


# ---------------------------------------------------------------------------
# Coercer helpers (private)
# ---------------------------------------------------------------------------

def _to_decimal(v) -> Decimal | None:
    if v is None:
        return None
    try:
        s = str(v).strip().replace("$", "").replace(",", "")
        if s.lower() in {"nan", "none", ""}:
            return None
        d = Decimal(s)
        # Bloustein occasionally emits 0 for missing values; preserve as None
        if d == 0:
            return None
        return d
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


def _to_acreage(v) -> Decimal | None:
    """Acreage may legitimately be very small but non-zero. Distinct from money."""
    if v is None:
        return None
    try:
        s = str(v).strip().replace(",", "")
        if s.lower() in {"nan", "none", ""}:
            return None
        d = Decimal(s)
        return d if d > 0 else None
    except (InvalidOperation, ValueError):
        return None


def _to_date(v) -> date | None:
    """Bloustein emits ISO YYYY-MM-DD strings despite the MMDDYY column name."""
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in {"nan", "none"}:
        return None
    # Try ISO first (the actual observed format)
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        pass
    # Defensive fallbacks for any year-specific drift
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _clean_str(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in {"nan", "none"}:
        return None
    return s


def _build_mailing_address(street: str | None, city_state: str | None) -> str | None:
    """Combine street_address + city_state into one mailing address string.

    Either-or-both may be missing. Returns None if BOTH are missing.
    """
    s = _clean_str(street)
    c = _clean_str(city_state)
    if s and c:
        return f"{s}, {c}"
    return s or c


# ---------------------------------------------------------------------------
# Public loader API
# ---------------------------------------------------------------------------

def parse_bloustein_year(csv_path: Path, year: int) -> pd.DataFrame:
    """Parse one mod_iv_YYYY.csv → DataFrame[CANONICAL_HISTORY_COLS]."""
    csv_path = Path(csv_path)
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        raise FileNotFoundError(f"missing or empty Bloustein CSV: {csv_path}")

    raw = pd.read_csv(csv_path, dtype=str, keep_default_na=False, na_values=[""])

    # Defensive Fair Haven filter — Bloustein CSVs are already FH-only, but if
    # the operator ever changes the collector, we don't silently emit other munis.
    if "mun_code_id" in raw.columns:
        before = len(raw)
        raw = raw[raw["mun_code_id"].astype(str).str.strip() == _FAIR_HAVEN_MUN_CODE_ID]
        if len(raw) == 0 and before > 0:
            raise ValueError(
                f"{csv_path.name}: no Fair Haven rows after mun_code_id filter "
                f"(got {before} rows but none match {_FAIR_HAVEN_MUN_CODE_ID!r})"
            )

    # Rename via BLOUSTEIN_TO_CANONICAL — keep ONLY mapped columns
    keep_cols = {src: dst for src, dst in BLOUSTEIN_TO_CANONICAL.items() if src in raw.columns}
    df = raw[list(keep_cols.keys())].rename(columns=keep_cols).copy()

    # Build parcel_pin from block / lot / qualifier
    def _pin(row):
        blk = _clean_str(row.get("_block")) or ""
        lot = _clean_str(row.get("_lot")) or ""
        qual = _clean_str(row.get("_qualifier")) or ""
        if not blk or not lot:
            return None
        return build_pams_pin(constants.MUN_CODE_FAIR_HAVEN, blk, lot, qual)

    df["parcel_pin"] = df.apply(_pin, axis=1)
    df = df[df["parcel_pin"].notna()].copy()

    # Owner mailing address composition
    df["owner_mailing_address"] = df.apply(
        lambda r: _build_mailing_address(r.get("_street_address"), r.get("_city_state")),
        axis=1,
    )

    # Year column (constant for this file)
    df["year"] = year

    # Coerce typed fields
    for money_col in ("land_value", "improvement_value", "net_value",
                      "deductions", "sale_price", "sale_assessment"):
        if money_col in df.columns:
            df[money_col] = df[money_col].map(_to_decimal)
        else:
            df[money_col] = None

    if "calculated_acreage" in df.columns:
        df["calculated_acreage"] = df["calculated_acreage"].map(_to_acreage)
    else:
        df["calculated_acreage"] = None

    if "_year_built_raw" in df.columns:
        df["year_built"] = df["_year_built_raw"].map(_to_int)
    else:
        df["year_built"] = None

    if "_num_dwellings_raw" in df.columns:
        df["num_dwellings"] = df["_num_dwellings_raw"].map(_to_int)
    else:
        df["num_dwellings"] = None

    if "_deed_date_raw" in df.columns:
        df["deed_date"] = df["_deed_date_raw"].map(_to_date)
    else:
        df["deed_date"] = None

    for str_col in ("prop_loc", "building_description", "deed_book",
                    "deed_page", "sale_nu_code"):
        if str_col in df.columns:
            df[str_col] = df[str_col].map(_clean_str)
        else:
            df[str_col] = None

    # Project to canonical schema (exact order, exact set)
    out = df.reindex(columns=CANONICAL_HISTORY_COLS)
    return out.reset_index(drop=True)


def parse_bloustein_all(snapshot_dir: Path) -> pd.DataFrame:
    """Parse every mod_iv_YYYY.csv in snapshot_dir → one frame keyed (parcel_pin, year)."""
    snapshot_dir = Path(snapshot_dir)
    if not snapshot_dir.exists() or not snapshot_dir.is_dir():
        raise FileNotFoundError(f"missing snapshot dir: {snapshot_dir}")

    paths = sorted(snapshot_dir.glob("mod_iv_[0-9][0-9][0-9][0-9].csv"))
    if not paths:
        raise FileNotFoundError(
            f"no mod_iv_YYYY.csv files in {snapshot_dir} "
            f"(run `python datasets/collect_bloustein.py`)"
        )

    frames: list[pd.DataFrame] = []
    for p in paths:
        m = _FILENAME_YEAR_RE.search(p.name)
        if not m:
            continue
        year = int(m.group(1))
        frames.append(parse_bloustein_year(p, year))

    if not frames:
        return pd.DataFrame(columns=CANONICAL_HISTORY_COLS)
    return pd.concat(frames, ignore_index=True)
