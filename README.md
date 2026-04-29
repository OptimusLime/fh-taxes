# Fair Haven Tax Assessment Analysis

See `.planning/PROJECT.md` for full context. v1 scope: 21 requirements, 3 phases.

## Quickstart

```bash
uv sync
make acquire    # downloads ~3 raw datasets to data/raw/<source>/<date>/
make all        # acquire + ingest + validate
```

No Jupyter, no Quarto, no notebooks — categorical project rule.
No SQLite, no PostGIS — Parquet + GeoParquet only.

See `make help` for all targets.
