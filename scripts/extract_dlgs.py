#!/usr/bin/env python
"""Parse the DLGS Property Tax Tables xls and rewrite constants.py.

Reads the "Municipal Tax Summary" sheet, finds the Fair Haven row by
MuniCode == constants.MUN_CODE_FAIR_HAVEN_DLGS ("1313"), and populates:
    TAX_RATE_PER_HUNDRED  (computed: total_levy / net_valuation_taxable * 100)
    TOTAL_LEVY
    NET_VALUATION_TAXABLE
    LEVY_BREAKDOWN        (dict of all levy components from the row)
"""
from __future__ import annotations

import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from fairhaven_tax import constants
from fairhaven_tax.ingest import dlgs
from fairhaven_tax.ingest.manifest import verify_manifest


CONSTANTS_PATH = Path("src/fairhaven_tax/constants.py")


def _to_decimal(v) -> Decimal | None:
    if v is None:
        return None
    try:
        s = str(v).strip().replace("$", "").replace(",", "")
        if s.lower() in {"nan", "none", ""}:
            return None
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _latest_snapshot() -> Path:
    base = Path("data/raw/dlgs_tax_tables")
    if not base.exists():
        raise FileNotFoundError(f"missing {base}; run `make acquire-dlgs`")
    snaps = sorted([d for d in base.iterdir() if d.is_dir()])
    if not snaps:
        raise FileNotFoundError(f"no snapshots in {base}")
    return snaps[-1]


def _find_workbook(snap: Path) -> Path:
    for ext in ("*.xls", "*.xlsx"):
        for p in snap.glob(ext):
            return p
    raise FileNotFoundError(f"no .xls/.xlsx in {snap}")


def _scan_workbook(path: Path) -> dict[str, Decimal]:
    """Return {semantic_name: Decimal} for the Fair Haven row in Municipal Tax Summary."""
    import xlrd

    wb = xlrd.open_workbook(str(path))
    if dlgs.SHEET_NAME not in wb.sheet_names():
        raise ValueError(
            f"sheet {dlgs.SHEET_NAME!r} not in workbook {path.name}; "
            f"sheets: {wb.sheet_names()}"
        )
    sh = wb.sheet_by_name(dlgs.SHEET_NAME)

    # Header row is row index 1 (verified). Row 0 is a multi-cell super-header.
    header = [str(sh.cell_value(1, c)).strip() for c in range(sh.ncols)]
    # Map header text → column index
    col_for_header: dict[str, int] = {}
    for c, h in enumerate(header):
        if h:
            col_for_header[h] = c

    # Find all configured columns
    resolved: dict[str, int] = {}
    for header_text, semantic in dlgs.COLUMNS.items():
        if header_text in col_for_header:
            resolved[semantic] = col_for_header[header_text]

    if "muni_code" not in resolved:
        raise ValueError(
            f"required column 'MuniCode' not found. Headers: {header[:30]}"
        )

    # Find Fair Haven row
    target = constants.MUN_CODE_FAIR_HAVEN_DLGS
    for r in range(2, sh.nrows):
        v = sh.cell_value(r, resolved["muni_code"])
        # MuniCode may come as float (1313.0) or string. Normalize.
        muni_str = str(int(v)) if isinstance(v, float) and v.is_integer() else str(v).strip()
        if muni_str == target:
            row_values: dict[str, Decimal] = {}
            for sem, col in resolved.items():
                if sem in ("muni_code", "municipality", "county"):
                    continue
                d = _to_decimal(sh.cell_value(r, col))
                if d is not None:
                    row_values[sem] = d
            row_values["muni_code"] = Decimal(target)  # for sanity
            return row_values

    raise ValueError(
        f"MuniCode {target!r} (Fair Haven Borough) not found in {path.name}"
    )


def _rewrite_constants(values: dict[str, Decimal]) -> None:
    """Rewrite constants.py with extracted values via regex substitution."""
    text = CONSTANTS_PATH.read_text()

    nvt = values.get("net_valuation_taxable")
    total_levy = values.get("total_levy")
    if nvt is None or total_levy is None:
        raise ValueError(
            f"net_valuation_taxable or total_levy missing from extracted values: "
            f"{list(values.keys())}"
        )

    # Compute per-$100 rate
    tax_rate = (total_levy / nvt * Decimal("100")).quantize(Decimal("0.001"))

    # Sanity check
    if not (Decimal("0.5") <= tax_rate <= Decimal("3.0")):
        print(f"WARN: computed tax_rate=${tax_rate}/$100 outside expected $0.50-$3.00 range")

    # Build LEVY_BREAKDOWN dict literal
    breakdown_keys = [
        "county_general", "county_library", "county_health", "county_open_space",
        "total_county", "local_school", "regional_school", "muni_school",
        "total_school", "local_municipal", "muni_open_space", "minimum_library",
        "total_municipal", "total_levy",
    ]
    # Map our DLGS column semantics → public breakdown keys
    dlgs_to_public = {
        "county_general_levy": "county_general",
        "county_library_levy": "county_library",
        "county_health_levy": "county_health",
        "county_open_space_levy": "county_open_space",
        "total_county_levy": "total_county",
        "local_school_levy": "local_school",
        "regional_school_levy": "regional_school",
        "muni_school_levy": "muni_school",
        "total_school_levy": "total_school",
        "local_municipal_levy": "local_municipal",
        "muni_open_space_levy": "muni_open_space",
        "minimum_library_tax": "minimum_library",
        "total_municipal_levy": "total_municipal",
        "total_levy": "total_levy",
    }
    parts = []
    for dlgs_key, public_key in dlgs_to_public.items():
        if dlgs_key in values:
            parts.append(f'"{public_key}": Decimal("{values[dlgs_key]}")')
    breakdown_repr = "{" + ", ".join(parts) + "}"

    text = re.sub(
        r"^TAX_RATE_PER_HUNDRED:.*$",
        f'TAX_RATE_PER_HUNDRED: Decimal | None = Decimal("{tax_rate}")',
        text, flags=re.MULTILINE,
    )
    text = re.sub(
        r"^TOTAL_LEVY:.*$",
        f'TOTAL_LEVY: Decimal | None = Decimal("{total_levy}")',
        text, flags=re.MULTILINE,
    )
    text = re.sub(
        r"^NET_VALUATION_TAXABLE:.*$",
        f'NET_VALUATION_TAXABLE: Decimal | None = Decimal("{nvt}")',
        text, flags=re.MULTILINE,
    )
    text = re.sub(
        r"^LEVY_BREAKDOWN:.*$",
        f"LEVY_BREAKDOWN: dict[str, Decimal] | None = {breakdown_repr}",
        text, flags=re.MULTILINE,
    )
    CONSTANTS_PATH.write_text(text)
    return tax_rate


def main() -> int:
    try:
        snap = _latest_snapshot()
        wb_path = _find_workbook(snap)
        ok, errors = verify_manifest(snap)
        if not ok:
            print(f"ERROR: manifest verification failed in {snap}:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 2
        values = _scan_workbook(wb_path)
        tax_rate = _rewrite_constants(values)
        print(f"Extracted DLGS values for Fair Haven (MuniCode {constants.MUN_CODE_FAIR_HAVEN_DLGS}):")
        for k, v in sorted(values.items()):
            if k == "muni_code":
                continue
            print(f"  {k}: ${v:,}")
        print(f"\nComputed tax rate: ${tax_rate} per $100")
        return 0
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
