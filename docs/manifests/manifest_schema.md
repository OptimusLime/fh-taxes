# manifest.json — Raw Snapshot Manifest

Per D-06. One per `data/raw/{source}/{YYYY-MM-DD}/` directory.

## Schema

```json
{
  "source": "njgin_monmouth_parcels | dlgs_tax_tables | sr1a",
  "retrieved_at": "2026-04-29T14:32:11Z",
  "files": [
    {
      "filename": "Monmouth_Parcels_and_MODIV.zip",
      "source_url": "https://...",
      "sha256": "abc123...",
      "bytes": 184521024,
      "etag": "\"opaque\"",
      "last_modified": "2026-03-15T08:00:00Z"
    }
  ],
  "notes": {
    "coverage_years": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
  }
}
```

## Reproducibility contract

- `source_url` + `sha256` are sufficient to re-fetch and verify any byte the pipeline ever consumed.
- `retrieved_at` is ISO-8601 UTC, `Z`-suffixed.
- `bytes` is the exact size on disk after download.
- `etag` and `last_modified` are best-effort (pulled from HTTP response headers when present).
- `notes` is free-form; SR1A uses it for `coverage_years`.
