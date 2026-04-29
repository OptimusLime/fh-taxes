"""NJ DLGS Property Tax Tables acquisition constants.

Index page: https://www.nj.gov/dca/dlgs/resources/Property_Tax_info.shtml
Annual workbooks live under: /dca/dlgs/resources/Property_Tax/{YY}_data/{YY}taxes.xls
(legacy .xls format, NOT .xlsx — verified live 2026-04-29 for 2017-2025).

Workbook of interest: sheet "Municipal Tax Summary".
Fair Haven row identified by MuniCode = "1313" (NOTE: NJGIN uses 1314 for Fair Haven —
DLGS uses a different muni-code scheme. See constants.MUN_CODE_FAIR_HAVEN_DLGS).
"""

SOURCE_NAME = "dlgs_tax_tables"


def url_for_year(year: int) -> str:
    """Return the canonical DLGS yearly tax tables URL.

    Tax year `2025` lives at `/Property_Tax/25_data/25taxes.xls` (two-digit year prefix).
    """
    yy = f"{year % 100:02d}"
    return f"https://www.nj.gov/dca/dlgs/resources/Property_Tax/{yy}_data/{yy}taxes.xls"


def archive_filename(year: int) -> str:
    yy = f"{year % 100:02d}"
    return f"{yy}taxes.xls"


# Defaults for the most recent tax year. Acquisition scripts may override via env var.
DEFAULT_YEAR = 2025
SOURCE_URL = url_for_year(DEFAULT_YEAR)
ARCHIVE_FILENAME = archive_filename(DEFAULT_YEAR)

# Sheet + column names inside the workbook (verified against 25taxes.xls 2026-04-29):
SHEET_NAME = "Municipal Tax Summary"

# Column header → semantic name (header is on row index 1, data starts row 2)
COLUMNS: dict[str, str] = {
    "MuniCode": "muni_code",                                 # e.g. "1313" for Fair Haven
    "Municipality": "municipality",                          # "Fair Haven Borough"
    "County": "county",
    "Net Valuation Taxable": "net_valuation_taxable",
    "Net County Taxes Apportioned Less State Aid": "county_general_levy",
    "County Library Taxes": "county_library_levy",
    "County Health Services Taxes": "county_health_levy",
    "County Open Space Preservation Trust Fund": "county_open_space_levy",
    "Total County Levy": "total_county_levy",
    "As Required by District School Budget": "local_school_levy",
    "Regional Consolidated and Joint School Budget": "regional_school_levy",
    "As Required by Local Municipal Budget": "muni_school_levy",
    "Total School Levy": "total_school_levy",
    "Local Municipal Purposes": "local_municipal_levy",
    "Local Municipal Open Space": "muni_open_space_levy",
    "Minimum Library Tax": "minimum_library_tax",
    "Total Local Municipal Tax Levy": "total_municipal_levy",
    "Total Levy on Which Tax Rate is Computed": "total_levy",
}
