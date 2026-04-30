"""Parse OPRS tax-list PDF page → 6-field dict for one parcel (D-32 taxlist subset).

The OPRS taxlist.cgi endpoint returns a multi-parcel page covering many
contiguous parcels in a single Borough's tax list. To extract a single
parcel's tax-paid record we therefore require the caller to specify the
target (block, lot) pair.

The taxlist row format is a 4-line block per parcel:

    line 0:   {block}  {land_dims}  n/a  {land}  {total}  {ded_cd}  {ded_amt}
    line 1:   {lot}    {bldg_desc}  {class}  {address}  [billing_code]  {improvement}
    line 2:   {city, state zip}     {net_taxable}  {2026_total_tax}
    line 3:   {acreage}  {prop_loc_short}  {special_tax_code}  {2026_1H_tax}

The 2H tax is not printed; it equals total - 1H within rounding.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber

TAXLIST_FIELDS = [
    "actual_tax_paid_total",
    "tax_1h_paid",
    "tax_2h_paid",
    "special_tax_codes",
    "deduction_codes",
    "deduction_amount",
]


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


def _extract_text(path: Path) -> str:
    try:
        with pdfplumber.open(str(path)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        joined = "\n".join(pages)
        if joined.strip():
            return joined
    except Exception:
        pass
    try:
        from pdfminer.high_level import extract_text

        return extract_text(str(path)) or ""
    except Exception:
        return ""


# A parcel-block first line:  "{block} {dims} n/a {land} {total} {ded_cd} {ded_amt}"
# - block: bare digits (no comma)
# - dims: alphanumeric with X / IRR  e.g. "35X160IRR"
# - n/a is the owner-redacted token in this Bloustein-style export
# - land/total: integers (no commas)
# - ded_cd: 2-digit code (e.g. "01", "02")
# - ded_amt: ".00" or "{integer}.00"
_LINE0_RE = re.compile(
    r"^(\d+)\s+\S+\s+n/a\s+(\d+)\s+(\d+)\s+(\d{2})\s+(\d*\.\d+)\s*$",
    re.M,
)


def _empty_result() -> dict[str, object]:
    return {
        "actual_tax_paid_total": None,
        "tax_1h_paid": None,
        "tax_2h_paid": None,
        "special_tax_codes": [],
        "deduction_codes": [],
        "deduction_amount": None,
    }


def parse_taxlist_pdf(
    path: Path, block: str, lot: str
) -> dict[str, object]:
    """Parse one parcel's tax-paid record out of a multi-parcel tax-list page.

    Args:
        path: Path to a taxlist_{year}.pdf file.
        block: Block number to locate, e.g. "30".
        lot: Lot number to locate, e.g. "1".

    Returns:
        dict with all TAXLIST_FIELDS keys.

        - When the parcel is not found in the page → all-None scalars and
          empty lists.
        - Lists (special_tax_codes, deduction_codes) are always returned as
          lists (never None).
        - deduction_amount is Decimal('0') (not None) when codes are present
          but the amount is .00, per zero-not-none rule.
    """
    path = Path(path)
    text = _extract_text(path)
    result = _empty_result()
    if not text.strip():
        return result

    block = str(block).strip()
    lot = str(lot).strip()

    lines = text.split("\n")
    # Find a line-0 match for the requested block whose immediately-following
    # line starts with the requested lot.
    for idx, line in enumerate(lines):
        m = _LINE0_RE.match(line)
        if not m:
            continue
        if m.group(1) != block:
            continue
        # Confirm the next non-empty line begins with the requested lot
        # token (a bare integer at the start of a 4-token-ish row).
        next_line = lines[idx + 1] if idx + 1 < len(lines) else ""
        next_first = next_line.split(" ", 1)[0] if next_line else ""
        if next_first != lot:
            continue

        # Located the parcel. Extract values.
        ded_code = m.group(4)
        ded_amt = _to_decimal(m.group(5))
        result["deduction_codes"] = [ded_code]
        # Zero deductions still yield Decimal('0'), not None.
        result["deduction_amount"] = (
            ded_amt if ded_amt is not None else Decimal("0")
        )

        # Line 2: city/state/zip ... net_taxable total_tax
        # The last numeric token on line 2 is the 2026 total tax (with
        # decimals). The second-to-last is the net taxable value.
        if idx + 2 < len(lines):
            line2_tokens = lines[idx + 2].split()
            # Pick the last token that parses as a Decimal with a "."
            for tok in reversed(line2_tokens):
                if "." in tok:
                    val = _to_decimal(tok)
                    if val is not None:
                        result["actual_tax_paid_total"] = val
                        break

        # Line 3: acreage prop_loc... special_tax_code 1H_tax
        if idx + 3 < len(lines):
            line3_tokens = lines[idx + 3].split()
            # The last token is the 1H tax (with decimal).
            if line3_tokens:
                last = line3_tokens[-1]
                if "." in last:
                    result["tax_1h_paid"] = _to_decimal(last)
                # Special tax code is the token immediately preceding the
                # 1H tax — a short integer.
                if len(line3_tokens) >= 2:
                    second_last = line3_tokens[-2]
                    if second_last.isdigit():
                        result["special_tax_codes"] = [second_last]

        # Compute 2H = total - 1H (not printed in the layout).
        total = result["actual_tax_paid_total"]
        one_h = result["tax_1h_paid"]
        if isinstance(total, Decimal) and isinstance(one_h, Decimal):
            result["tax_2h_paid"] = total - one_h

        break

    return result
