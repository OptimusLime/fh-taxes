"""Collect Fair Haven MOD-IV historical CSVs from Rutgers Bloustein.

Replaces /tmp/pull_bloustein.sh and /tmp/redo_bloustein.sh.

Usage:
    uv run python datasets/collect_bloustein.py            # default: 1989-2025, ~30s pace
    uv run python datasets/collect_bloustein.py --years 2017 2018
    uv run python datasets/collect_bloustein.py --rate 0.5 --jitter-pct 0.2

Idempotent: existing valid CSVs (≥ MIN_ROWS) are skipped. Partial/failed
files are detected and re-fetched. Atomic writes — no half-finished CSVs
ever land in the snapshot dir.

Auth credentials are read from ENV (preferred) or fall back to constants below.
Set FAIRHAVEN_BLOUSTEIN_EMAIL and FAIRHAVEN_BLOUSTEIN_PASSWORD before running
to avoid checking secrets into git.
"""
from __future__ import annotations

import argparse
import os
import random
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests


LOGIN_URL = "https://modiv.rutgers.edu/login/"
SEARCH_URL = "https://modiv.rutgers.edu/search-data/"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
FAIR_HAVEN_MUNIS_CODE = "234"
DEFAULT_DL_LIMIT = 10000
EXPECTED_MIN_ROWS = 2000  # Fair Haven typical ~2,120-2,210 records/year


@dataclass
class Config:
    years: list[int]
    rate_per_second: float
    jitter_pct: float
    output_dir: Path
    min_rows: int
    max_attempts: int
    email: str
    password: str


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _login(session: requests.Session, email: str, password: str) -> None:
    """Acquire session cookies via login form POST."""
    session.headers.update({"User-Agent": USER_AGENT})
    r = session.post(
        LOGIN_URL,
        data={"userEmail": email, "userLoginPassword": password},
        timeout=30,
        allow_redirects=True,
    )
    r.raise_for_status()
    if "/dashboard/" not in r.url:
        raise RuntimeError(
            f"login failed — landed at {r.url}; check FAIRHAVEN_BLOUSTEIN_EMAIL/PASSWORD"
        )


def _download_year(
    session: requests.Session, year: int, out_path: Path, dl_limit: int = DEFAULT_DL_LIMIT
) -> tuple[int, int]:
    """POST search-data with download-data action; return (http_status, row_count).

    Atomic write: download to .tmp sibling, validate row count, then rename.
    """
    payload = [
        ("api", "true"),
        ("action", "download-data"),
        ("munisCode", FAIR_HAVEN_MUNIS_CODE),
        ("years[]", str(year)),
        ("limit", ""),
        ("dlLimit", str(dl_limit)),
        ("qualifId", ""),
        ("propUseCodeId", ""),
        ("propClassCodeId", ""),
        ("eplOwnId", ""),
        ("eplUseId", ""),
        ("eplDescId", ""),
        ("exemptId", ""),
        ("sptaxId", ""),
        ("sr1aId", ""),
        ("propertyAddress", ""),
        ("blockText", ""),
        ("lotText", ""),
        ("breakByYear", "false"),
    ]
    r = session.post(SEARCH_URL, data=payload, timeout=120, stream=True)
    status = r.status_code
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Write to .tmp first; only rename to final on success
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    rows = 0
    try:
        with open(tmp_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if chunk:
                    f.write(chunk)
                    rows += chunk.count(b"\n")
        if status == 200 and rows >= 1:
            tmp_path.replace(out_path)
        else:
            tmp_path.unlink(missing_ok=True)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return status, rows


def _file_is_valid(path: Path, min_rows: int) -> bool:
    if not path.exists() or path.stat().st_size < 1000:
        return False
    with open(path, "rb") as f:
        rows = sum(1 for _ in f)
    return rows >= min_rows


def _sleep(rate: float, jitter_pct: float) -> None:
    base = 1.0 / rate if rate > 0 else 0.0
    jitter = base * jitter_pct * (random.random() * 2 - 1)
    delay = max(0.1, base + jitter)
    time.sleep(delay)


def collect(cfg: Config) -> int:
    log_path = cfg.output_dir / "_collect.log"
    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    def log(msg: str) -> None:
        line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
        print(line, flush=True)
        with open(log_path, "a") as f:
            f.write(line + "\n")

    session = requests.Session()
    log(f"Logging in as {cfg.email}")
    _login(session, cfg.email, cfg.password)
    log(f"Logged in. Output: {cfg.output_dir}")

    failures: list[int] = []
    for year in cfg.years:
        out_path = cfg.output_dir / f"mod_iv_{year}.csv"
        if _file_is_valid(out_path, cfg.min_rows):
            log(f"  {year}: cached ({out_path.stat().st_size}b), skipping")
            continue

        for attempt in range(1, cfg.max_attempts + 1):
            try:
                status, rows = _download_year(session, year, out_path)
            except Exception as e:
                log(f"  {year}: attempt {attempt}/{cfg.max_attempts} EXC {type(e).__name__}: {e}")
                _sleep(cfg.rate_per_second, cfg.jitter_pct)
                continue
            if _file_is_valid(out_path, cfg.min_rows):
                size = out_path.stat().st_size
                log(f"  {year}: ✓ attempt {attempt} status={status} rows={rows} size={size}")
                break
            else:
                log(
                    f"  {year}: attempt {attempt}/{cfg.max_attempts} BAD "
                    f"status={status} rows={rows} (need ≥{cfg.min_rows}) — retrying"
                )
            _sleep(cfg.rate_per_second, cfg.jitter_pct)
        else:
            log(f"  {year}: FAILED after {cfg.max_attempts} attempts")
            failures.append(year)

        _sleep(cfg.rate_per_second, cfg.jitter_pct)

    log(f"Collection complete. Failures: {failures or 'none'}")
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect Fair Haven MOD-IV history from Rutgers Bloustein")
    parser.add_argument("--years", nargs="*", type=int, default=list(range(1989, 2026)),
                        help="Years to collect (default 1989-2025)")
    parser.add_argument("--rate", dest="rate_per_second", type=float, default=1.0 / 30.0,
                        help="Requests per second (default 1/30 = 30s pace)")
    parser.add_argument("--jitter-pct", type=float, default=0.15,
                        help="Random jitter as fraction of base interval (default 0.15)")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help=f"Snapshot dir (default data/raw/bloustein_modiv/<today>/)")
    parser.add_argument("--min-rows", type=int, default=EXPECTED_MIN_ROWS,
                        help=f"Reject CSVs with fewer rows (default {EXPECTED_MIN_ROWS})")
    parser.add_argument("--max-attempts", type=int, default=4,
                        help="Retry attempts per year (default 4)")
    args = parser.parse_args()

    email = os.environ.get("FAIRHAVEN_BLOUSTEIN_EMAIL")
    password = os.environ.get("FAIRHAVEN_BLOUSTEIN_PASSWORD")
    if not email or not password:
        print(
            "ERROR: set FAIRHAVEN_BLOUSTEIN_EMAIL and FAIRHAVEN_BLOUSTEIN_PASSWORD env vars.",
            file=sys.stderr,
        )
        return 2

    out_dir = args.output_dir or Path(f"data/raw/bloustein_modiv/{_today_utc()}")
    cfg = Config(
        years=sorted(args.years),
        rate_per_second=args.rate_per_second,
        jitter_pct=args.jitter_pct,
        output_dir=out_dir,
        min_rows=args.min_rows,
        max_attempts=args.max_attempts,
        email=email,
        password=password,
    )
    return collect(cfg)


if __name__ == "__main__":
    sys.exit(main())
