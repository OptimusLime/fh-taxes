"""NJ DLGS Property Tax Tables acquisition constants."""

SOURCE_NAME = "dlgs_tax_tables"
# DLGS publishes annual `YYtaxes.xls` files. URL pattern observed in CONTEXT.md:
# https://nj.gov/dca/dlgs/resources/Property_Tax_info.shtml hosts the index.
# Direct file URL pattern (verify on first run; format has drifted between .xls / .xlsx):
SOURCE_URL_2025 = "https://www.nj.gov/dca/dlgs/resources/property_tax_docs/25taxes.xlsx"
# If 2025 file is .xls (legacy), override via FAIRHAVEN_DLGS_URL env var.
ARCHIVE_FILENAME_2025 = "25taxes.xlsx"
