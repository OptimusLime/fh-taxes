"""NJ DOT SR1A annual sales acquisition constants and fixed-width record layout.

SR1A is published as fixed-width 663-byte records (one record per line),
zipped per calendar year. The layout is documented at
https://www.nj.gov/treasury/taxation/pdf/lpt/SR1Afilelayout.pdf.

Public coverage on NJ Treasury's statdata page is **2020-2025** (six years).
2018 and 2019 are NOT publicly available there. PROJECT.md / REQUIREMENTS.md
originally specified 2018-2025; this has been narrowed to match reality.

Source page: https://www.nj.gov/treasury/taxation/lpt/statdata.shtml
"""

SOURCE_NAME = "sr1a"
COVERAGE_YEARS = list(range(2020, 2026))  # 2020..2025 inclusive (6 years)


def url_for_year(year: int) -> str:
    """Return the canonical NJ Treasury SR1A download URL for a year."""
    return f"https://www.nj.gov/treasury/taxation/lpt/statdata/Sales{year}.zip"


def archive_for_year(year: int) -> str:
    return f"Sales{year}.zip"


def inner_filename_for_year(year: int) -> str:
    """The .txt member inside the zip is named like the archive."""
    return f"Sales{year}.txt"


# ---- Fixed-width record layout (per SR1Afilelayout.pdf) -------------------
#
# Each record is 663 bytes. Field positions below are 1-indexed start, length
# (matching the PDF). The parser converts to 0-indexed slices internally.
#
# Field name                      start  length    type
# ------------------------------- -----  ------    ----------------
RECORD_LENGTH = 663

FIELDS: dict[str, tuple[int, int]] = {
    # (start_1indexed, length)
    "county_code":          (1, 2),    # numeric, e.g. "13" for Monmouth
    "district_code":        (3, 2),    # numeric, e.g. "14" for Fair Haven
    "total_assessment":     (5, 12),   # 9(12) zero-padded
    "operator_initials":    (17, 3),
    "last_update_date":     (20, 6),   # YYMMDD
    # 26-33 filler (8)
    "un_type":              (34, 1),   # X — flag, often 'N' or blank
    "nu_code":              (35, 3),   # XXX — "  " (blank) or "01"-"33", possibly with trailing space
    "reported_sales_price": (38, 9),
    "verified_sales_price": (47, 9),
    "main_assessed_land":   (56, 9),
    "main_assessed_bldg":   (65, 9),
    "main_assessed_total":  (74, 9),
    "sales_ratio":          (83, 5),   # S999V99 — signed implied-decimal
    "realty_transfer_fee":  (88, 9),
    "rtf_error_flag":       (97, 1),
    "rtf_exempt_code":      (98, 1),
    "serial_number":        (99, 7),
    # 106-109 filler
    "grantor_name":         (110, 35),
    "grantor_street":       (145, 25),
    "grantor_city_state":   (170, 25),
    "grantor_zip":          (195, 9),
    "grantee_name":         (204, 35),
    "grantee_street":       (239, 25),
    "grantee_city_state":   (264, 25),
    "grantee_zip":          (289, 9),
    "property_location":    (298, 25),
    "aging_date":           (323, 6),
    "deed_book":            (329, 5),
    "deed_page":            (334, 5),
    "deed_date":            (339, 6),  # YYMMDD
    "date_recorded":        (345, 6),  # YYMMDD
    "block":                (351, 5),
    "block_suffix":         (356, 4),
    "lot":                  (360, 5),
    "lot_suffix":           (365, 4),
    "etc":                  (369, 1),
    # 370-619: ADDL-{BLOCK,LOT,QUALIFIER,VALUES} × 5 — additional lots
    "qualification_codes":  (620, 5),
    "assess_year":          (625, 2),
    "property_class":       (627, 3),
    "class_4_type":         (630, 3),
    # 633-638 filler
    "assessor_nu_code":     (639, 3),
    "field_status_code":    (642, 1),
    "field_date":           (643, 6),
    "critical_error_flag":  (649, 1),
    # 650-652 filler
    "year_built":           (653, 4),
    "living_space":         (657, 7),  # sqft proxy — usable for hedonic
}


def slice_field(record: str, name: str) -> str:
    """Extract a field by name from a 663-byte record, returning the raw stripped string."""
    start, length = FIELDS[name]
    # Convert 1-indexed start to 0-indexed
    return record[start - 1 : start - 1 + length].strip()
