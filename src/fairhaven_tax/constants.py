"""Project-wide constants. Tax rate / levy values are populated by `make extract-dlgs`
from the live DLGS Property Tax Tables.

Real-data calibration as of tax year 2025 (verified 2026-04-29 against
25taxes.xls and parcels_gdb_Monmouth.zip):

  - Fair Haven NJGIN MUN code:           "1314"   (parcels.MUN, tax_list.CD_CODE)
  - Fair Haven DLGS MuniCode:            "1313"   (different scheme)
  - Fair Haven SR1A district code:       "14"     (county=13 + district=14)
  - Class-2 residential parcels (real):  2064
  - Aggregate NET_VALUE class-2 (real):  $2,740,871,000
  - Net Valuation Taxable all classes:   $2,827,194,216 (per DLGS Municipal Tax Summary)
  - Total Levy 2025:                     $40,339,309.77 (per DLGS)
  - Implied general tax rate:            ~$1.427 per $100 (40.34M / 2.827B × 100)

Note: PROJECT.md originally cited $1.574/$100 — that figure does not match the
DLGS-published 2025 numbers. `make extract-dlgs` populates the live values below.
"""
from decimal import Decimal

# Municipality identifiers
MUN_CODE_FAIR_HAVEN: str = "1314"            # NJGIN parcels.MUN / tax_list.CD_CODE
MUN_CODE_FAIR_HAVEN_DLGS: str = "1313"       # DLGS Municipal Tax Summary "MuniCode"
SR1A_COUNTY_MONMOUTH: str = "13"             # SR1A cols 1-2
SR1A_DISTRICT_FAIR_HAVEN: str = "14"         # SR1A cols 3-4
PROPERTY_CLASS_RESIDENTIAL: str = "2"        # MOD-IV class 2

# SR1A NU codes considered arms-length per NJ Director's Ratio convention.
#
# Per NJ DOT / IAAO: NU code is BLANK (or "0"/"00") when the transaction is USABLE
# (arms-length) for ratio analysis. Codes 01-33 enumerate the various Non-Usable
# categories (compulsion, related parties, sheriff sales, corrective deeds, etc.).
#
# Empirically verified against Fair Haven Sales2020-2025: blank NU = ~30-40
# transactions/year, which matches the expected residential turnover for a
# ~2,200-parcel borough.
ARMS_LENGTH_NU_CODES: frozenset[str] = frozenset({"", "0", "00"})

# CRS
CRS_NATIVE: str = "EPSG:3424"   # NAD83 / New Jersey State Plane US ft (NJGIN distribution)
CRS_EXPORT: str = "EPSG:4326"   # WGS84 — Phase 3 GeoJSON export only

# Validation tolerances and expected values (derived from real 2025 NJGIN snapshot)
VALIDATION_TOLERANCE: Decimal = Decimal("0.05")  # ±5% per DATA-01
EXPECTED_PARCEL_COUNT: int = 2064                # real class-2 count (was 2200 stub)
EXPECTED_AGGREGATE_ASSESSED: Decimal = Decimal("2_740_871_000")  # real NET_VALUE sum

# SR1A coverage 2020-2025 = 6 years; expect at least ~150 arms-length sales total.
SR1A_MIN_ARMS_LENGTH_SALES: int = 100  # generous floor; real value is ~197

# Populated by `make extract-dlgs` from DLGS Municipal Tax Summary.
# Decimal preserves the published precision.
TAX_RATE_PER_HUNDRED: Decimal | None = Decimal("1.427")
TOTAL_LEVY: Decimal | None = Decimal("40339309.769999996")
NET_VALUATION_TAXABLE: Decimal | None = Decimal("2827194216.0")
LEVY_BREAKDOWN: dict[str, Decimal] | None = {"county_general": Decimal("5056823.6"), "county_library": Decimal("322177.91"), "county_health": Decimal("0.0"), "county_open_space": Decimal("763431.36"), "total_county": Decimal("6142432.87"), "local_school": Decimal("18036963.0"), "regional_school": Decimal("7366280.0"), "muni_school": Decimal("0.0"), "total_school": Decimal("25403243.0"), "local_municipal": Decimal("8793633.9"), "muni_open_space": Decimal("0.0"), "minimum_library": Decimal("0.0"), "total_municipal": Decimal("8793633.9"), "total_levy": Decimal("40339309.769999996")}
# Keys when populated:
#   "county_general", "county_library", "county_health", "county_open_space",
#   "total_county", "local_school", "regional_school", "muni_school", "total_school",
#   "local_municipal", "muni_open_space", "minimum_library", "total_municipal",
#   "total_levy"

# ---------------------------------------------------------------------------
# Phase 2 — Statistical Pipeline thresholds and reproducibility constants
# ---------------------------------------------------------------------------

# Reproducibility (D-67) — Plan 4, 5, 7
RANDOM_SEED: int = 42

# IAAO Standard on Ratio Studies (April 2013) — Plan 6
# Source: assessr R formulas.R cod_met / prd_met / prb_met (RESEARCH.md §3)
IAAO_COD_RESIDENTIAL_MAX: Decimal = Decimal("15.0")     # percent
IAAO_COD_RESIDENTIAL_MIN: Decimal = Decimal("5.0")      # percent
IAAO_PRD_MIN: Decimal = Decimal("0.98")
IAAO_PRD_MAX: Decimal = Decimal("1.03")
IAAO_PRB_MIN: Decimal = Decimal("-0.05")
IAAO_PRB_MAX: Decimal = Decimal("0.05")

# Hedonic spec (D-54) — Plan 4
HEDONIC_TRAIN_YEAR_MIN: int = 2020
HEDONIC_TRAIN_YEAR_MAX: int = 2025
HEDONIC_K_NEIGHBORHOOD_DEFAULT: int = 6   # within {5..8}
HEDONIC_R2_TARGET: Decimal = Decimal("0.7")  # MODEL-02

# CDF gap test (D-55, D-66) — Plan 7
# Defaults from assessr::detect_chasing (RESEARCH.md §4.1)
CDF_GAP_BOUNDS: tuple[Decimal, Decimal] = (Decimal("0.98"), Decimal("1.02"))
CDF_GAP_THRESHOLD: Decimal = Decimal("0.03")
CDF_TEST_YEAR_MIN: int = 2014   # post-ADP regime per D-55
CDF_TEST_YEAR_MAX: int = 2025
CDF_TEST_MIN_N: int = 30        # assessr soft warning threshold

# Historical Fair Haven general tax rates per $100 (D-52: yearly correctness within regime).
# Source: DLGS Property Tax Tables (cached under data/raw/dlgs_tax_tables/).
# Missing years fall back to the 2025 verified rate (1.427) with a limitation_flag
# set in downstream outputs (Plan 05).
HISTORICAL_TAX_RATES: dict[int, Decimal] = {
    2025: Decimal("1.427"),  # verified DLGS 2025 25taxes.xls (cached under data/raw/dlgs_tax_tables/2026-04-29/)
    # Other years populated by the historical-rate extractor;
    # missing entries trigger fallback-to-2025 + limitation_flag in Plan 05 outputs.
}
HISTORICAL_TAX_RATES_FALLBACK: Decimal = Decimal("1.427")  # used when year missing
