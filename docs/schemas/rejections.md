# Rejections Schema (`data/processed/rejections.parquet`)

**Format:** Parquet, zstd compression
**Purpose:** Audit trail of every SR1A row filtered out during ingest. Required by D-12.

## Columns

| Column             | Type      | Nullable | Description                                                                              |
|--------------------|-----------|----------|------------------------------------------------------------------------------------------|
| `parcel_pin`       | string    | yes      | PAMS_PIN if buildable; null if district/block/lot were unparseable.                      |
| `sale_date`        | date      | yes      | Parsed sale date if successful; null if rejection reason is `unparseable_date`.          |
| `sale_price`       | decimal   | yes      | Parsed sale price if successful; null if rejection reason is `unparseable_price`.        |
| `nu_code`          | string    | yes      | Normalized NU code if available.                                                         |
| `deed_ref`         | string    | yes      | `f"{deed_book}/{deed_page}"` when both present, else null.                               |
| `rejection_reason` | string    | no       | One of the controlled vocabulary values listed below.                                    |
| `source_file`      | string    | no       | Original archive filename.                                                               |
| `source_year`      | int16     | no       | SR1A coverage year.                                                                      |

## Controlled Vocabulary — `rejection_reason`

| Value                       | Meaning                                                                       |
|-----------------------------|-------------------------------------------------------------------------------|
| `nu_code_not_arms_length`   | NU code not in `SR1A_ARMS_LENGTH_NU_CODES` (D-12).                            |
| `district_not_fair_haven`   | `district` ≠ `"14"` after zfill(2). SR1A is statewide; we keep only FH.       |
| `unparseable_date`          | `SALE_DATE` could not be coerced to a date.                                   |
| `unparseable_price`         | `SALE_PRICE` could not be coerced to a `Decimal`.                             |
| `unmapped_column`           | Required canonical column missing from year mapper (schema drift).            |
| `missing_required_field`    | One of `district / block / lot` was null after normalization.                 |

## Notes

- Filter ordering during parse (rows are routed to rejections at the first failed gate):
  1. `district_not_fair_haven`
  2. `missing_required_field`
  3. `nu_code_not_arms_length`
  Date/price parse failures attach independently when coercion fails.
- This file is non-blocking: rows here do not cause validation to fail. They exist for audit only.
