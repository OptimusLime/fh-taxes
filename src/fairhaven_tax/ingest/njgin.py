"""NJGIN Monmouth Parcels + MOD-IV acquisition constants.

The FGDB ZIP is published as an ArcGIS Hub "Document Link" item at
`https://njogis-newjersey.opendata.arcgis.com/documents/372377f86745436b821f2f4b93485be6/about`.
The Hub's metadata API resolves that item to the actual download URL below.

Verified live 2026-04-29.
"""

SOURCE_NAME = "njgin_monmouth_parcels"
SOURCE_URL = "https://geoapps.nj.gov/njgin/parcel/parcels_gdb_Monmouth.zip"
ARCHIVE_FILENAME = "parcels_gdb_Monmouth.zip"

# The download host (geoapps.nj.gov) is fronted by Imperva and rejects bare User-Agents.
# Acquisition scripts MUST send a browser-like User-Agent + Referer.
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Referer": "https://njogis-newjersey.opendata.arcgis.com/",
}

# Inside the ZIP, the FGDB is at MonmouthCounty.gdb/. Two layers exist:
#   - "parcels": polygons keyed by PAMS_PIN, fields: PAMS_PIN, MUN, BLOCK, LOT, QCODE, ...
#   - "tax_list": MOD-IV records (no geometry), fields: GIS_PIN, CD_CODE, BLOCK, LOT,
#     QUALIFIER, PROP_CLASS, NET_VALUE, LAND_VAL, IMPRVT_VAL, DEED_DATE, SALE_PRICE,
#     SALES_CODE (NU code), YR_CONSTR, CALC_ACRE, DWELL, BLDG_CLASS, etc.
# The two are joined on parcels.PAMS_PIN == tax_list.GIS_PIN.
GDB_DIRNAME = "MonmouthCounty.gdb"
PARCELS_LAYER = "parcels"
TAX_LIST_LAYER = "tax_list"
