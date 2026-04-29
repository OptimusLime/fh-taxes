"""Parquet / GeoParquet read+write helpers. D-01: never SQLite, never PostGIS."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

PROCESSED_DIR = Path("data/processed")


def ensure_processed_dir(base: Path | None = None) -> Path:
    """Create and return data/processed/ (or override base for testing)."""
    p = Path(base) if base is not None else PROCESSED_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_parquet(
    df: pd.DataFrame,
    path: str | Path,
    schema: pa.Schema | None = None,
    compression: str = "zstd",
    metadata: dict[str, str] | None = None,
) -> Path:
    """Write a pandas DataFrame to parquet via pyarrow.

    Args:
        df: Source DataFrame (Decimals preserved as object dtype).
        path: Destination path.
        schema: Optional pyarrow Schema override.
        compression: zstd by default.
        metadata: Optional schema-level metadata as str→str dict.

    Returns:
        Resolved Path written.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)
    if metadata:
        merged = dict(table.schema.metadata or {})
        for k, v in metadata.items():
            merged[k.encode()] = v.encode()
        table = table.replace_schema_metadata(merged)
    pq.write_table(table, p, compression=compression)
    return p


def write_geoparquet(
    gdf: gpd.GeoDataFrame,
    path: str | Path,
    compression: str = "zstd",
) -> Path:
    """Write a GeoDataFrame to GeoParquet. Refuses to write CRS-less frames."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if gdf.crs is None:
        raise ValueError("GeoDataFrame has no CRS; refusing to write")
    gdf.to_parquet(p, compression=compression)
    return p


def read_parquet(path: str | Path) -> pd.DataFrame:
    """Read a non-geo parquet file via pyarrow."""
    return pq.read_table(Path(path)).to_pandas()


def read_geoparquet(path: str | Path) -> gpd.GeoDataFrame:
    """Read a GeoParquet file via geopandas."""
    return gpd.read_parquet(Path(path))
