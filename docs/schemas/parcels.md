# Parcels Schema (`data/processed/parcels.parquet`)

**Format:** GeoParquet (geopandas-native), zstd compression
**CRS:** EPSG:3424 (NAD83 / New Jersey State Plane US ft) — D-13
**Primary key:** `pams_pin`
**Filter:** `MUN_CODE == "1314"` AND `PROPERTY_CLASS == "2"` (Fair Haven class-2 residential)

## Columns

| Column                    | Type            | Nullable | Description                                                                                  |
|---------------------------|-----------------|----------|----------------------------------------------------------------------------------------------|
| `pams_pin`                | string          | no       | Primary key, format `f"{district}_{block}_{lot}_{qualifier}"` (qualifier "" if absent).      |
| `mun_code`                | string          | no       | Constant `"1314"`.                                                                            |
| `district`                | string          | no       | Constant `"14"` (Fair Haven SR1A district).                                                   |
| `block`                   | string          | no       | MOD-IV block (string, leading zeros / letter suffixes preserved).                             |
| `lot`                     | string          | no       | MOD-IV lot.                                                                                   |
| `qualifier`               | string          | no       | MOD-IV qualifier or `""` if none.                                                             |
| `property_class`          | string          | no       | Constant `"2"` (residential).                                                                 |
| `assessed_value`          | decimal         | no       | Total net assessed value (NET_VALUE).                                                         |
| `land_value`              | decimal         | yes      | Land component.                                                                               |
| `improvement_value`       | decimal         | yes      | Improvement component.                                                                        |
| `year_built`              | int32           | yes      | YR_CONSTR.                                                                                    |
| `sqft`                    | int32           | yes      | BLDG_SQFT.                                                                                    |
| `lot_size_acres`          | decimal         | yes      | ACREAGE.                                                                                      |
| `bedrooms`                | int16           | yes      | Bedrooms (if MOD-IV exposes; else null).                                                      |
| `bathrooms`               | decimal         | yes      | Bathrooms (decimal because halves).                                                           |
| `waterfront_flag`         | bool            | no       | Default `false` in Phase 1; Phase 2 may refine.                                               |
| `modiv_last_sale_date`    | date            | yes      | MOD-IV's last-sale-date field (raw).                                                          |
| `modiv_last_sale_price`   | decimal         | yes      | MOD-IV's last-sale-price field (raw).                                                         |
| `modiv_last_sale_nu_code` | string          | yes      | MOD-IV's last-sale NU code (raw).                                                             |
| `last_sale_date`          | date            | yes      | Resolved last arms-length sale date (Task 2). Sourced from SR1A or MOD-IV.                    |
| `last_sale_price`         | decimal         | yes      | Resolved last arms-length sale price.                                                          |
| `last_sale_nu_code`       | string          | yes      | Resolved last arms-length sale NU code.                                                       |
| `last_sale_source`        | string          | yes      | `"sr1a"` if from SR1A, `"modiv"` if fallback, null if neither.                                |
| `geometry`                | polygon         | no       | Parcel polygon in EPSG:3424.                                                                  |

## Notes

- Decimals are persisted as Python `Decimal` objects in pandas object columns. Phase 2 may convert
  to `pyarrow.decimal128` for downstream perf if needed.
- D-15: pipeline hard-fails if input CRS is not EPSG:3424.
- D-18 last-sale resolution: MAX(sale_date), tie-break MAX(sale_price).
- Reprojection to EPSG:4326 is reserved for Phase 3 (D-14).
