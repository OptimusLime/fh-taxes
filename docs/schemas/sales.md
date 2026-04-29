# Sales Schema (`data/processed/sales.parquet`)

**Format:** Parquet (no geometry), zstd compression
**Primary key:** `(parcel_pin, sale_date, sale_price, source_year)` (no enforced PK; SR1A may have
multiple deeds in a single day for a single parcel — see D-18 tie-break logic).
**Filter:** `district == "14"` AND `nu_code ∈ {"0", "07", "10", "26", "33"}` (D-12)

## Columns

| Column             | Type      | Nullable | Description                                                                  |
|--------------------|-----------|----------|------------------------------------------------------------------------------|
| `parcel_pin`       | string    | no       | PAMS_PIN, `f"{district}_{block}_{lot}_{qualifier}"`.                         |
| `sale_date`        | date      | no       | Sale date (parsed from SR1A `SALE_DATE`).                                    |
| `sale_price`       | decimal   | no       | Sale price (Decimal; `$` and `,` stripped).                                  |
| `nu_code`          | string    | no       | Two-character zero-padded NU code, ∈ {"0", "07", "10", "26", "33"}. Special: bare "0" / "00" both normalize to "0". |
| `deed_book`        | string    | yes      | Deed book reference.                                                         |
| `deed_page`        | string    | yes      | Deed page reference.                                                         |
| `grantor_redacted` | bool      | no       | Daniel's Law redaction flag from SR1A (post-2024 SR1A files redact grantor). |
| `source_file`      | string    | no       | Original archive filename (e.g. `sr1a-2024.zip`).                            |
| `source_year`      | int16     | no       | SR1A coverage year (2018..2025).                                             |

## Notes

- Decimal preservation: `sale_price` is `Decimal`, never `float`.
- NU code normalization: `lambda x: "0" if str(x).strip() in {"0", "00"} else str(x).strip().zfill(2)`.
  This preserves the canonical `SR1A_ARMS_LENGTH_NU_CODES` set ({"0", "07", "10", "26", "33"}).
- Last-sale resolution per parcel uses MAX(sale_date), tie-break MAX(sale_price) — see D-18 and
  `validate/reconcile.py::resolve_last_arms_length_sale`.
