"""Download NJ DLGS 2025 Property Tax Tables. Per DATA-02 + D-06."""
from __future__ import annotations

import os
import sys

from fairhaven_tax.ingest import dlgs
from fairhaven_tax.ingest.manifest import (
    download_with_manifest_entry,
    snapshot_dir,
    write_manifest,
)


def main() -> int:
    url = os.environ.get("FAIRHAVEN_DLGS_URL", dlgs.SOURCE_URL_2025)
    d = snapshot_dir(dlgs.SOURCE_NAME)
    dest = d / dlgs.ARCHIVE_FILENAME_2025
    print(f"[dlgs] downloading {url} -> {dest}", flush=True)
    try:
        entry = download_with_manifest_entry(url, dest)
    except Exception as e:
        print(f"[dlgs] FAILED: {e}", file=sys.stderr)
        print(
            "[dlgs] If DLGS file format has drifted (.xls vs .xlsx), set "
            "FAIRHAVEN_DLGS_URL and re-run.",
            file=sys.stderr,
        )
        return 2
    write_manifest(d, source=dlgs.SOURCE_NAME, entries=[entry])
    print(f"[dlgs] OK sha256={entry.sha256} bytes={entry.bytes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
