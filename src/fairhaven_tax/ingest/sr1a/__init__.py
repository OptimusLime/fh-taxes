"""NJ DOT SR1A annual sales acquisition constants."""

SOURCE_NAME = "sr1a"
COVERAGE_YEARS = list(range(2018, 2026))  # 2018..2025 inclusive


# NJ Treasury hosts SR1A annual files at /treasury/taxation/lpt/statdata.shtml
# The exact per-year file URLs are published in the index page; pattern is:
# https://www.nj.gov/treasury/taxation/lpt/sr1a/sr1a-{YYYY}.zip (observed pattern;
# if a year drifts from this pattern, supply via FAIRHAVEN_SR1A_URL_{YYYY} env var).
def url_for_year(year: int) -> str:
    return f"https://www.nj.gov/treasury/taxation/lpt/sr1a/sr1a-{year}.zip"


def archive_for_year(year: int) -> str:
    return f"sr1a-{year}.zip"
