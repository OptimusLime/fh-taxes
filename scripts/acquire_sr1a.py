"""Download SR1A 2018-2025 annual files. Per DATA-03 + D-05/D-06."""
from __future__ import annotations

import os
import sys

from fairhaven_tax.ingest import sr1a
from fairhaven_tax.ingest.manifest import (
    ManifestEntry,
    download_with_manifest_entry,
    snapshot_dir,
    write_manifest,
)


def main() -> int:
    d = snapshot_dir(sr1a.SOURCE_NAME)
    entries: list[ManifestEntry] = []
    failures: list[tuple[int, str]] = []
    for year in sr1a.COVERAGE_YEARS:
        url = os.environ.get(f"FAIRHAVEN_SR1A_URL_{year}", sr1a.url_for_year(year))
        dest = d / sr1a.archive_for_year(year)
        print(f"[sr1a {year}] downloading {url} -> {dest}", flush=True)
        try:
            entries.append(download_with_manifest_entry(url, dest))
        except Exception as e:  # noqa: BLE001
            print(f"[sr1a {year}] FAILED: {e}", file=sys.stderr)
            failures.append((year, str(e)))
    if entries:
        write_manifest(
            d,
            source=sr1a.SOURCE_NAME,
            entries=entries,
            notes={
                "coverage_years": [
                    int(e.filename.split("-")[1].split(".")[0]) for e in entries
                ],
                "failed_years": [y for y, _ in failures],
            },
        )
    if failures:
        print(
            f"[sr1a] {len(failures)} year(s) failed: "
            f"{[y for y, _ in failures]}. Set FAIRHAVEN_SR1A_URL_<YYYY> "
            "for any rotated URLs and re-run.",
            file=sys.stderr,
        )
        return 2 if not entries else 1  # partial success returns 1
    print(f"[sr1a] OK {len(entries)} years")
    return 0


if __name__ == "__main__":
    sys.exit(main())
