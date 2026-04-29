from __future__ import annotations

import json
from pathlib import Path

from fairhaven_tax.ingest.manifest import (
    ManifestEntry,
    sha256_file,
    snapshot_dir,
    verify_manifest,
    write_manifest,
)


def test_write_and_verify_manifest_roundtrip(tmp_path: Path) -> None:
    # Arrange: write a fake "downloaded" file
    d = tmp_path / "raw" / "fake_source" / "2026-04-29"
    d.mkdir(parents=True)
    payload = b"hello fair haven"
    f = d / "fake.bin"
    f.write_bytes(payload)
    digest = sha256_file(f)

    # Act
    entry = ManifestEntry(
        filename="fake.bin",
        source_url="https://example.test/fake.bin",
        sha256=digest,
        bytes=len(payload),
    )
    write_manifest(d, source="fake_source", entries=[entry])

    # Assert: manifest exists and verify_manifest returns ok
    assert (d / "manifest.json").exists()
    ok, errors = verify_manifest(d)
    assert ok, errors

    data = json.loads((d / "manifest.json").read_text())
    assert data["source"] == "fake_source"
    assert data["files"][0]["sha256"] == digest
    assert data["files"][0]["bytes"] == len(payload)
    assert data["retrieved_at"].endswith("Z")


def test_verify_manifest_detects_corruption(tmp_path: Path) -> None:
    d = tmp_path / "raw" / "fake_source" / "2026-04-29"
    d.mkdir(parents=True)
    f = d / "fake.bin"
    f.write_bytes(b"original")
    entry = ManifestEntry(
        filename="fake.bin",
        source_url="https://example.test/fake.bin",
        sha256=sha256_file(f),
        bytes=f.stat().st_size,
    )
    write_manifest(d, source="fake_source", entries=[entry])

    # Tamper
    f.write_bytes(b"tampered_with")
    ok, errors = verify_manifest(d)
    assert not ok
    assert any("sha256 mismatch" in e for e in errors)


def test_snapshot_dir_creates_dated_path(tmp_path: Path) -> None:
    p = snapshot_dir("test_source", base=tmp_path, date="2026-04-29")
    assert p == tmp_path / "test_source" / "2026-04-29"
    assert p.is_dir()
