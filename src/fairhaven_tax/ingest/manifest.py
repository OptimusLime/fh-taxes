"""Manifest writer/verifier for raw snapshot directories (D-05/D-06)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MANIFEST_FILENAME = "manifest.json"
_CHUNK = 1 << 20  # 1 MiB


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    filename: str
    source_url: str
    sha256: str
    bytes: int
    etag: str | None = None
    last_modified: str | None = None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def snapshot_dir(source: str, base: Path = Path("data/raw"), date: str | None = None) -> Path:
    """Return data/raw/{source}/{YYYY-MM-DD}/ — creates if missing."""
    d = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    p = base / source / d
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_manifest(
    directory: Path,
    source: str,
    entries: list[ManifestEntry],
    notes: dict[str, Any] | None = None,
) -> Path:
    """Write manifest.json atomically. Overwrites if exists."""
    payload = {
        "source": source,
        "retrieved_at": utcnow_iso(),
        "files": [asdict(e) for e in entries],
        "notes": notes or {},
    }
    target = directory / MANIFEST_FILENAME
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True))
    tmp.replace(target)
    return target


def verify_manifest(directory: Path) -> tuple[bool, list[str]]:
    """Return (ok, errors). For each file in manifest, recompute sha256 and compare."""
    manifest_path = directory / MANIFEST_FILENAME
    if not manifest_path.exists():
        return False, [f"missing {manifest_path}"]
    data = json.loads(manifest_path.read_text())
    errors: list[str] = []
    for entry in data["files"]:
        fp = directory / entry["filename"]
        if not fp.exists():
            errors.append(f"missing file: {fp}")
            continue
        actual = sha256_file(fp)
        if actual != entry["sha256"]:
            errors.append(
                f"sha256 mismatch for {entry['filename']}: "
                f"manifest={entry['sha256']}, disk={actual}"
            )
        if fp.stat().st_size != entry["bytes"]:
            errors.append(
                f"size mismatch for {entry['filename']}: "
                f"manifest={entry['bytes']}, disk={fp.stat().st_size}"
            )
    return (len(errors) == 0), errors


def download_with_manifest_entry(
    url: str, dest: Path, session=None, timeout: int = 120
) -> ManifestEntry:
    """Stream-download URL to dest, return a ManifestEntry. Caller writes manifest."""
    import requests
    sess = session or requests.Session()
    sess.headers.setdefault(
        "User-Agent",
        "fairhaven_tax_research/0.1 (research; contact: paul@atelico.studio)",
    )
    with sess.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        etag = r.headers.get("ETag")
        last_modified = r.headers.get("Last-Modified")
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        with tmp.open("wb") as f:
            for chunk in r.iter_content(chunk_size=_CHUNK):
                if chunk:
                    f.write(chunk)
        tmp.replace(dest)
    return ManifestEntry(
        filename=dest.name,
        source_url=url,
        sha256=sha256_file(dest),
        bytes=dest.stat().st_size,
        etag=etag,
        last_modified=last_modified,
    )
