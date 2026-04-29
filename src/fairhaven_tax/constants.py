"""Project-wide constants. Tax rate / levy values are populated by Plan 2 from DLGS data.

Per D-02, the 2025/2026 Fair Haven general tax rate is $1.574 per $100 of assessed value.
Six-component breakdown (muni / county / library / local-school / regional-school / open-space)
and TOTAL_LEVY are written here by scripts/extract_dlgs.py in Plan 2.
"""
from decimal import Decimal

# Municipality identifiers (DATA-01 / D-12 filter)
MUN_CODE_FAIR_HAVEN: str = "1314"  # NJGIN MUN_CODE
SR1A_DISTRICT_FAIR_HAVEN: str = "14"  # SR1A district code (Monmouth = 13xx; FH = 14)
PROPERTY_CLASS_RESIDENTIAL: str = "2"  # MOD-IV class 2

# SR1A NU codes considered arms-length per IAAO + NJ DOT documentation (D-12)
SR1A_ARMS_LENGTH_NU_CODES: frozenset[str] = frozenset({"0", "07", "10", "26", "33"})
# Note: NJ DOT publishes some NU codes zero-padded ("07"), some not ("7"). The ingest layer
# MUST normalize to two-character zero-padded strings before membership test. Do NOT change
# the set without revisiting D-12 + REQUIREMENTS DATA-03.

# CRS (D-13 / D-14)
CRS_NATIVE: str = "EPSG:3424"  # NAD83 / New Jersey State Plane US ft — NJGIN distribution CRS
CRS_EXPORT: str = "EPSG:4326"  # WGS84 — Phase 3 GeoJSON export only

# Validation tolerances (D-10 / D-11)
VALIDATION_TOLERANCE: Decimal = Decimal("0.05")  # ±5% per DATA-01
EXPECTED_PARCEL_COUNT: int = 2200
EXPECTED_AGGREGATE_ASSESSED: Decimal = Decimal("2_770_000_000")  # $2.77B
SR1A_MIN_ARMS_LENGTH_SALES_2018_2025: int = 200  # sanity floor (D-11)

# Populated by Plan 2 (DATA-02). Decimal preserves the published precision.
TAX_RATE_PER_HUNDRED: Decimal | None = None
TOTAL_LEVY: Decimal | None = None
LEVY_BREAKDOWN: dict[str, Decimal] | None = None
# Keys when populated: "municipal", "county", "library", "local_school",
# "regional_school", "open_space"
