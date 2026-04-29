"""NJGIN Monmouth Parcels + MOD-IV acquisition constants."""

SOURCE_NAME = "njgin_monmouth_parcels"
# NJGIN Open Data Hub publishes the Monmouth County parcel + MOD-IV joined dataset.
# The download URL is the FGDB ZIP. As of 2026-Q1 the canonical URL is below; if
# NJGIN rotates URLs, update here and bump the snapshot date.
SOURCE_URL = (
    "https://njogis-newjersey.opendata.arcgis.com/api/download/v1/items/"
    "MONMOUTH_PARCELS_MODIV/file?layers=0&format=fgdb"
)
# NOTE: The exact ArcGIS Hub item GUID may need updating. The acquisition script
# supports overriding via the FAIRHAVEN_NJGIN_URL env var so a researcher can
# pin a freshly-fetched URL without code change.
ARCHIVE_FILENAME = "Monmouth_Parcels_and_MODIV.zip"
