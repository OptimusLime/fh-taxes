"""Tests for scripts/build_parcels_geojson.py.

Covers:
  - Happy path: synthetic 3-parcel GeoDataFrame in EPSG:3424 → GeoJSON in
    EPSG:4326, exactly 3 features, owner_name absent, properties subset of
    the D-65 whitelist.
  - Preflight: missing parquet → exit 2.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

# Make scripts/ importable for direct main() invocation.
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import build_parcels_geojson  # noqa: E402


def _synthetic_parcels() -> gpd.GeoDataFrame:
    """3 parcels in EPSG:3424 with both whitelisted and forbidden columns.

    Includes `owner_name` to exercise the D-65 footprint-isolation whitelist:
    after the script runs, the column must NOT appear in the output GeoJSON.
    """
    df = pd.DataFrame(
        {
            "pams_pin": ["1314_30_1", "1314_30_2", "1314_30_3"],
            "block": ["30", "30", "30"],
            "lot": ["1", "2", "3"],
            "mun": ["1314", "1314", "1314"],
            "property_location": ["1 RIVER RD", "2 RIVER RD", "3 RIVER RD"],
            "owner_name": ["DOE JOHN", "ROE JANE", "POE PAUL"],  # MUST be stripped
            "assessed_value": [100, 200, 300],  # also not in whitelist
        }
    )
    # NJ State Plane (EPSG:3424) — coordinates roughly near Fair Haven.
    geoms = [
        Point(596000, 540000),
        Point(596100, 540100),
        Point(596200, 540200),
    ]
    return gpd.GeoDataFrame(df, geometry=geoms, crs="EPSG:3424")


def test_main_writes_geojson_with_d65_whitelist(tmp_path, monkeypatch):
    """Happy path: 3 synthetic parcels → 3-feature GeoJSON in EPSG:4326,
    owner_name stripped, properties ⊆ whitelist."""
    base_path = tmp_path / "data" / "processed" / "parcels.parquet"
    out_path = tmp_path / "viz" / "src" / "data" / "parcels.geojson"
    base_path.parent.mkdir(parents=True, exist_ok=True)

    gdf = _synthetic_parcels()
    gdf.to_parquet(base_path)

    monkeypatch.setattr(build_parcels_geojson, "BASE", base_path)
    monkeypatch.setattr(build_parcels_geojson, "OUT", out_path)

    rc = build_parcels_geojson.main()
    assert rc == 0, "main() must succeed on valid input"
    assert out_path.exists()

    # Read back as GeoJSON.
    result = gpd.read_file(out_path)

    # Exactly 3 features.
    assert len(result) == 3

    # CRS is EPSG:4326 (Leaflet's expectation).
    assert result.crs is not None
    epsg = result.crs.to_epsg()
    assert epsg == 4326, f"expected EPSG:4326, got {epsg}"

    # D-65 enforcement: owner_name MUST NOT appear in output columns.
    assert "owner_name" not in result.columns, (
        "D-65 violation: owner_name leaked into published GeoJSON"
    )

    # All retained property columns are within the whitelist.
    allowed = set(build_parcels_geojson.PROPERTY_COLS) | {"geometry"}
    assert set(result.columns).issubset(allowed), (
        f"unexpected columns in GeoJSON: {set(result.columns) - allowed}"
    )

    # Spot-check feature properties at the JSON level too.
    raw = json.loads(out_path.read_text())
    assert raw["type"] == "FeatureCollection"
    assert len(raw["features"]) == 3
    for feat in raw["features"]:
        props = feat["properties"]
        assert "owner_name" not in props
        assert set(props.keys()).issubset(set(build_parcels_geojson.PROPERTY_COLS))
        assert "pams_pin" in props


def test_main_returns_2_when_parquet_missing(tmp_path, monkeypatch):
    """Preflight: BASE doesn't exist → exit 2."""
    missing = tmp_path / "nope.parquet"
    out_path = tmp_path / "out.geojson"
    monkeypatch.setattr(build_parcels_geojson, "BASE", missing)
    monkeypatch.setattr(build_parcels_geojson, "OUT", out_path)

    rc = build_parcels_geojson.main()
    assert rc == 2
    assert not out_path.exists()
