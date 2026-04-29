"""Per-year SR1A parser. Uses YAML column mappers (D-16) to canonical schema (D-17).

Filters per D-12: only NU codes ∈ {0, 07, 10, 26, 33}, district == 14.
Routes failures to rejections.parquet with controlled vocabulary reasons.
"""
from __future__ import annotations

import io
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
import yaml

from fairhaven_tax import constants
from fairhaven_tax.ingest.pams_pin import build_pams_pin


COLUMNS_DIR = Path(__file__).parent / "columns"

CANONICAL_SALES_COLS = [
    "parcel_pin",
    "sale_date",
    "sale_price",
    "nu_code",
    "deed_book",
    "deed_page",
    "grantor_redacted",
    "source_file",
    "source_year",
]
CANONICAL_REJECT_COLS = [
    "parcel_pin",
    "sale_date",
    "sale_price",
    "nu_code",
    "deed_ref",
    "rejection_reason",
    "source_file",
    "source_year",
]


def _normalize_nu_code(x) -> str:
    """D-12 normalization: '0' and '00' both map to '0'; otherwise zfill(2)."""
    s = str(x).strip()
    if s in {"0", "00"}:
        return "0"
    return s.zfill(2)


def _zfill_2(x) -> str:
    return str(x).strip().zfill(2)


def _coerce_decimal(x) -> Decimal | None:
    if x is None:
        return None
    try:
        s = str(x).strip().replace("$", "").replace(",", "")
        if s.lower() in {"nan", "none", ""}:
            return None
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _read_csv_from_zip(archive_path: Path) -> tuple[pd.DataFrame, str]:
    """Open a SR1A zip; return (DataFrame, inner_filename). CSV/TXT only.

    Raises NotImplementedError for DBF (deferred until needed).
    """
    with zipfile.ZipFile(archive_path) as zf:
        members = zf.namelist()
        # Prefer CSV/TXT
        delim_candidates = [m for m in members if m.lower().endswith((".csv", ".txt"))]
        if not delim_candidates:
            dbfs = [m for m in members if m.lower().endswith(".dbf")]
            if dbfs:
                raise NotImplementedError(
                    f"DBF SR1A files not yet supported ({archive_path.name}); "
                    "add a dbfread/geopandas reader to ingest/sr1a/parse.py "
                    "or convert the DBF to CSV out-of-band."
                )
            raise ValueError(f"no CSV/TXT/DBF found in {archive_path}")
        inner = sorted(delim_candidates)[0]
        raw = zf.read(inner)

    # Try delimiters in order
    text = raw.decode("utf-8", errors="replace")
    for sep in (",", "|", "\t"):
        try:
            df = pd.read_csv(io.StringIO(text), sep=sep, dtype=str, keep_default_na=False)
            if df.shape[1] >= 3:
                return df, inner
        except Exception:
            continue
    raise ValueError(f"could not parse {archive_path} as delimited text")


def parse_sr1a_year(archive_path: Path, year: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse one SR1A year archive → (sales_df, rejections_df).

    Both DataFrames conform to docs/schemas/sales.md and docs/schemas/rejections.md.
    """
    archive_path = Path(archive_path)
    yaml_path = COLUMNS_DIR / f"{year}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"missing column mapper: {yaml_path}")
    cfg = yaml.safe_load(yaml_path.read_text())
    mapping: dict[str, str] = cfg.get("mapping", {})
    types: dict[str, str] = cfg.get("types", {})

    raw_df, inner_name = _read_csv_from_zip(archive_path)

    # Apply mapping (rename source columns to canonical names; drop unmapped)
    keep = {src: canon for src, canon in mapping.items() if src in raw_df.columns}
    df = raw_df[list(keep.keys())].rename(columns=keep).copy()

    # Track per-row rejection reason (first hit wins)
    n = len(df)
    rejection_reason: list[str | None] = [None] * n

    # Type coercions
    if "sale_date" in df.columns and types.get("sale_date") == "date":
        parsed = pd.to_datetime(df["sale_date"], format="%m/%d/%Y", errors="coerce")
        # Fall back to mixed-format parse for any NaT
        nat_mask = parsed.isna()
        if nat_mask.any():
            fallback = pd.to_datetime(df["sale_date"][nat_mask], errors="coerce")
            parsed.loc[nat_mask] = fallback
        df["sale_date"] = parsed.dt.date
        for i, v in enumerate(parsed.isna().tolist()):
            if v and rejection_reason[i] is None:
                rejection_reason[i] = "unparseable_date"

    if "sale_price" in df.columns and types.get("sale_price") == "decimal":
        coerced = [_coerce_decimal(v) for v in df["sale_price"]]
        df["sale_price"] = coerced
        for i, v in enumerate(coerced):
            if v is None and rejection_reason[i] is None:
                rejection_reason[i] = "unparseable_price"

    if "nu_code" in df.columns and types.get("nu_code") == "string_zfill_2":
        df["nu_code"] = df["nu_code"].map(_normalize_nu_code)

    if "district" in df.columns and types.get("district") == "string_zfill_2":
        df["district"] = df["district"].map(_zfill_2)

    if "property_class" in df.columns and types.get("property_class") == "string":
        df["property_class"] = df["property_class"].astype(str).str.strip()

    # Build parcel_pin for every row (even those headed to rejections)
    qualifier_col = df["qualifier"] if "qualifier" in df.columns else [""] * n
    parcel_pins: list[str | None] = []
    for i in range(n):
        d = df["district"].iloc[i] if "district" in df.columns else None
        b = df["block"].iloc[i] if "block" in df.columns else None
        l = df["lot"].iloc[i] if "lot" in df.columns else None
        q = qualifier_col[i] if hasattr(qualifier_col, "__getitem__") else ""
        if isinstance(qualifier_col, pd.Series):
            q = qualifier_col.iloc[i]
        if (
            d is None or str(d).strip() in {"", "nan"}
            or b is None or str(b).strip() in {"", "nan"}
            or l is None or str(l).strip() in {"", "nan"}
        ):
            parcel_pins.append(None)
            if rejection_reason[i] is None:
                rejection_reason[i] = "missing_required_field"
        else:
            parcel_pins.append(build_pams_pin(d, b, l, q))
    df["parcel_pin"] = parcel_pins

    # Filter ordering: district -> required -> nu_code (only if not already rejected)
    fh_district = constants.SR1A_DISTRICT_FAIR_HAVEN
    arms_length = constants.SR1A_ARMS_LENGTH_NU_CODES

    for i in range(n):
        if rejection_reason[i] is not None:
            continue
        # district check
        if "district" in df.columns:
            d = df["district"].iloc[i]
            if str(d) != fh_district:
                rejection_reason[i] = "district_not_fair_haven"
                continue
        # nu_code arms-length check
        if "nu_code" in df.columns:
            nc = df["nu_code"].iloc[i]
            if nc not in arms_length:
                rejection_reason[i] = "nu_code_not_arms_length"
                continue

    # Build deed_ref for rejections
    if "deed_book" in df.columns and "deed_page" in df.columns:
        deed_refs = [
            f"{db}/{dp}" if (db and dp) else None
            for db, dp in zip(df["deed_book"], df["deed_page"])
        ]
    else:
        deed_refs = [None] * n
    df["deed_ref"] = deed_refs

    df["source_file"] = archive_path.name
    df["source_year"] = pd.Series([year] * n, dtype="int16")

    # grantor_redacted: bool
    if "grantor_redacted" in df.columns:
        gr = df["grantor_redacted"].astype(str).str.lower()
        df["grantor_redacted"] = gr.isin({"1", "true", "t", "yes", "y"})
    else:
        df["grantor_redacted"] = False

    # Ensure deed_book / deed_page exist
    for col in ("deed_book", "deed_page"):
        if col not in df.columns:
            df[col] = None

    # Split
    df["__rejection"] = rejection_reason
    accepted_mask = df["__rejection"].isna()
    sales = df.loc[accepted_mask, CANONICAL_SALES_COLS].reset_index(drop=True)
    rej = df.loc[~accepted_mask].copy()
    rej["rejection_reason"] = rej["__rejection"]
    rej_out = rej[CANONICAL_REJECT_COLS].reset_index(drop=True)

    return sales, rej_out


def parse_sr1a_all(snapshot_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse every sr1a-{YYYY}.zip in snapshot_dir; concatenate sales + rejections."""
    snapshot_dir = Path(snapshot_dir)
    sales_frames: list[pd.DataFrame] = []
    rej_frames: list[pd.DataFrame] = []
    archives = sorted(snapshot_dir.glob("sr1a-*.zip"))
    if not archives:
        raise FileNotFoundError(f"no sr1a-*.zip in {snapshot_dir}")
    for arch in archives:
        # Extract year from filename, e.g. sr1a-2024.zip -> 2024
        stem = arch.stem  # sr1a-2024
        try:
            year = int(stem.split("-")[-1])
        except ValueError:
            raise ValueError(f"cannot parse year from {arch.name}")
        s, r = parse_sr1a_year(arch, year)
        sales_frames.append(s)
        rej_frames.append(r)

    sales_all = (
        pd.concat(sales_frames, ignore_index=True)
        if sales_frames else pd.DataFrame(columns=CANONICAL_SALES_COLS)
    )
    rej_all = (
        pd.concat(rej_frames, ignore_index=True)
        if rej_frames else pd.DataFrame(columns=CANONICAL_REJECT_COLS)
    )
    return sales_all, rej_all
