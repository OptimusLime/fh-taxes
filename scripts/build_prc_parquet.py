#!/usr/bin/env python
"""Aggregate OPRS cache → data/processed/prc.parquet (D-32) + enrich sales.parquet (D-33).

Walks data/raw/oprs_prc/<pams_pin>/, runs each parser (parse_m4, parse_prc_pdf,
parse_ch75_pdf, parse_taxlist_pdf, parse_sr) on every parcel, joins their dicts
by pams_pin, and writes data/processed/prc.parquet (one row per parcel).

Side outputs:
- data/processed/prc_sqft_diffs.parquet — parcels where m4.square_ft and PRC
  livable_area diverge by >10% (non-blocking; mirrors D-19 reconciliation).
- data/processed/sales.parquet — overwritten with a left-join of the existing
  Phase 1 SR1A sales onto sr.cgi-derived columns per D-33.

Exit codes:
  0 — success
  2 — missing cache OR zero rows parsed (refusal-to-declare-success guard)
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd

from fairhaven_tax.ingest.oprs.parse_ch75_pdf import CH75_FIELDS, parse_ch75_pdf
from fairhaven_tax.ingest.oprs.parse_m4 import M4_FIELDS, parse_m4  # noqa: F401
from fairhaven_tax.ingest.oprs.parse_prc_pdf import PRC_PDF_FIELDS, parse_prc_pdf
from fairhaven_tax.ingest.oprs.parse_sr import SR_FIELDS, parse_sr  # noqa: F401
from fairhaven_tax.ingest.oprs.parse_taxlist_pdf import (
    TAXLIST_FIELDS,
    parse_taxlist_pdf,
)
from fairhaven_tax.persist.parquet_io import write_parquet

CACHE_ROOT = Path("data/raw/oprs_prc")
SALES_PATH = Path("data/processed/sales.parquet")
OUT_PRC = Path("data/processed/prc.parquet")
OUT_DIFFS = Path("data/processed/prc_sqft_diffs.parquet")


def _none_dict(keys) -> dict[str, object]:
    """Return {k: None for k in keys} — used when an optional component is missing."""
    return {k: None for k in keys}


def _aggregate_parcel(parcel_dir: Path) -> tuple[dict | None, list[dict]]:
    """Aggregate one parcel directory → (parcel_row, sale_rows).

    Args:
        parcel_dir: Path to a data/raw/oprs_prc/<pams_pin>/ directory.

    Returns:
        (None, []) when m4.html is missing — caller should log + skip.
        Otherwise (row_dict, list_of_sr_dicts). row_dict always carries every
        canonical key from M4_FIELDS + PRC_PDF_FIELDS + CH75_FIELDS +
        TAXLIST_FIELDS plus pams_pin. Missing PDFs yield None values.
    """
    m4_path = parcel_dir / "m4.html"
    if not m4_path.exists():
        return None, []

    row: dict[str, object] = {"pams_pin": parcel_dir.name}
    row.update(parse_m4(m4_path))
    # Ensure pams_pin from directory name wins (parse_m4 may rebuild it from
    # block/lot/qual but the cache directory name is the canonical join key).
    row["pams_pin"] = parcel_dir.name

    block = row.get("block")
    lot = row.get("lot")

    prc_path = parcel_dir / "prc.pdf"
    if prc_path.exists():
        try:
            row.update(parse_prc_pdf(prc_path))
        except Exception as e:
            print(f"WARN: parse_prc_pdf({parcel_dir.name}) raised {e!r}",
                  file=sys.stderr)
            row.update(_none_dict(PRC_PDF_FIELDS))
    else:
        row.update(_none_dict(PRC_PDF_FIELDS))

    ch75_path = parcel_dir / "ch75.pdf"
    if ch75_path.exists():
        try:
            row.update(parse_ch75_pdf(ch75_path))
        except Exception as e:
            print(f"WARN: parse_ch75_pdf({parcel_dir.name}) raised {e!r}",
                  file=sys.stderr)
            row.update(_none_dict(CH75_FIELDS))
    else:
        row.update(_none_dict(CH75_FIELDS))

    taxlist_paths = sorted(parcel_dir.glob("taxlist_*.pdf"))
    if taxlist_paths and block and lot:
        try:
            row.update(parse_taxlist_pdf(taxlist_paths[-1], block, lot))
        except Exception as e:
            print(f"WARN: parse_taxlist_pdf({parcel_dir.name}) raised {e!r}",
                  file=sys.stderr)
            row.update(_none_dict(TAXLIST_FIELDS))
    else:
        # Empty result mirrors parse_taxlist_pdf._empty_result(): lists not None.
        row.update({
            "actual_tax_paid_total": None,
            "tax_1h_paid": None,
            "tax_2h_paid": None,
            "special_tax_codes": [],
            "deduction_codes": [],
            "deduction_amount": None,
        })

    sale_rows: list[dict] = []
    for sr_path in sorted(parcel_dir.glob("sr_*.html")):
        if sr_path.name.endswith(".no_sale"):
            continue
        try:
            sr = parse_sr(sr_path)
        except Exception as e:
            print(f"WARN: parse_sr({sr_path.name}) raised {e!r}", file=sys.stderr)
            continue
        if sr is not None:
            sale_rows.append(sr)

    return row, sale_rows


def _cross_validate_sqft(df: pd.DataFrame) -> pd.DataFrame:
    """Compare m4.square_ft against PRC livable_area; return rows differing >10%.

    Returns DataFrame with columns: pams_pin, m4_sqft, livable_area, abs_diff_pct.
    Empty frame when no qualifying mismatches exist.
    """
    if "square_ft" not in df.columns or "livable_area" not in df.columns:
        return pd.DataFrame(
            columns=["pams_pin", "m4_sqft", "livable_area", "abs_diff_pct"]
        )

    out_rows = []
    for _, r in df.iterrows():
        m4 = r.get("square_ft")
        la = r.get("livable_area")
        if m4 is None or la is None:
            continue
        try:
            m4f = float(m4)
            laf = float(la)
        except (TypeError, ValueError):
            continue
        if m4f <= 0 or laf <= 0:
            continue
        denom = max(m4f, laf)
        diff_pct = abs(m4f - laf) / denom * 100.0
        if diff_pct > 10.0:
            out_rows.append({
                "pams_pin": r.get("pams_pin"),
                "m4_sqft": m4f,
                "livable_area": laf,
                "abs_diff_pct": diff_pct,
            })
    return pd.DataFrame(
        out_rows, columns=["pams_pin", "m4_sqft", "livable_area", "abs_diff_pct"]
    )


def main() -> int:
    if not CACHE_ROOT.exists():
        print(f"ERROR: missing {CACHE_ROOT}; run datasets/collect_oprs.py first",
              file=sys.stderr)
        return 2

    parcel_rows: list[dict] = []
    sale_rows_all: list[dict] = []
    parcels_seen = 0
    parcels_skipped = 0

    for d in sorted(CACHE_ROOT.iterdir()):
        if not d.is_dir():
            continue
        parcels_seen += 1
        try:
            row, sale_rows = _aggregate_parcel(d)
        except Exception as e:
            print(f"WARN: _aggregate_parcel({d.name}) raised {e!r}",
                  file=sys.stderr)
            parcels_skipped += 1
            continue
        if row is None:
            parcels_skipped += 1
            print(f"WARN: skipping {d.name} (no m4.html)", file=sys.stderr)
            continue
        parcel_rows.append(row)
        sale_rows_all.extend(sale_rows)

    if not parcel_rows:
        print("ERROR: zero parcels parsed — refusing to declare success",
              file=sys.stderr)
        return 2

    df_prc = pd.DataFrame(parcel_rows)
    write_parquet(df_prc, str(OUT_PRC))
    print(f"Wrote {len(df_prc)} parcel rows × {len(df_prc.columns)} cols → "
          f"{OUT_PRC} (seen={parcels_seen}, skipped={parcels_skipped})")

    # Cross-validation (non-blocking).
    diffs = _cross_validate_sqft(df_prc)
    if len(diffs) > 0:
        write_parquet(diffs, str(OUT_DIFFS))
        print(f"Wrote {len(diffs)} sqft-mismatch rows → {OUT_DIFFS}")
    else:
        print("No sqft mismatches > 10% (no diffs file written)")

    # Sales enrichment (D-33).
    if SALES_PATH.exists() and sale_rows_all:
        df_sr = pd.DataFrame(sale_rows_all)
        # De-dup sr rows on the join key (defensively — duplicate ssis would
        # cause a row-multiplying merge).
        df_sr = df_sr.drop_duplicates(subset=["parcel_pin", "sale_date"],
                                      keep="first")
        sales = pd.read_parquet(SALES_PATH)
        before = len(sales)
        sales_enriched = sales.merge(
            df_sr,
            on=["parcel_pin", "sale_date"],
            how="left",
            suffixes=("", "_sr"),
        )
        after = len(sales_enriched)
        if after != before:
            print(f"WARN: sales row count changed during merge: {before} → {after}",
                  file=sys.stderr)
        write_parquet(sales_enriched, str(SALES_PATH))
        new_cols = sorted(set(sales_enriched.columns) - set(sales.columns))
        print(f"Enriched {before} sales × {len(df_sr)} sr rows → {SALES_PATH}; "
              f"added {len(new_cols)} columns: {new_cols}")
    elif not SALES_PATH.exists():
        print(f"WARN: {SALES_PATH} not found — skipping sales enrichment",
              file=sys.stderr)
    else:
        print("WARN: no sr rows parsed — skipping sales enrichment",
              file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
