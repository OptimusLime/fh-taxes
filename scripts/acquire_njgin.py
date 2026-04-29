"""Download NJGIN Monmouth Parcels + MOD-IV FGDB to data/raw/njgin_monmouth_parcels/<date>/.

Per DATA-01 + D-05/D-06. URL override via FAIRHAVEN_NJGIN_URL.
"""
from __future__ import annotations

import os
import sys

from fairhaven_tax.ingest import njgin
from fairhaven_tax.ingest.manifest import (
    download_with_manifest_entry,
    snapshot_dir,
    write_manifest,
)


def main() -> int:
    url = os.environ.get("FAIRHAVEN_NJGIN_URL", njgin.SOURCE_URL)
    d = snapshot_dir(njgin.SOURCE_NAME)
    dest = d / njgin.ARCHIVE_FILENAME
    print(f"[njgin] downloading {url} -> {dest}", flush=True)
    try:
        entry = download_with_manifest_entry(url, dest)
    except Exception as e:
        print(f"[njgin] FAILED: {e}", file=sys.stderr)
        print(
            "[njgin] If NJGIN URL has rotated, set FAIRHAVEN_NJGIN_URL to the current "
            "ArcGIS Hub download URL and re-run.",
            file=sys.stderr,
        )
        return 2
    write_manifest(d, source=njgin.SOURCE_NAME, entries=[entry])
    print(f"[njgin] OK sha256={entry.sha256} bytes={entry.bytes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
