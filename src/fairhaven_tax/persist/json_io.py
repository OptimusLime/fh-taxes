"""Atomic JSON write helper (D-63 hot-reload contract).

Astro's dev server hot-reloads any change to `viz/src/data/**`. If a writer
emits the JSON in two pieces (truncate-then-write) Astro can pick up a
half-written file mid-stream and crash. Phase 2's contract is therefore
.tmp + atomic-rename for every JSON artifact under viz/src/data/.

This helper is the canonical entry point used by every Phase-2 script that
emits chart specs (`viz/src/data/charts/*.vl.json`) or per-PIN overlays
(`viz/src/data/overlays/*.json`).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path, payload: Any, *, indent: int = 2) -> None:
    """Write `payload` to `path` atomically via .tmp + rename.

    Uses `Path.replace()` rather than `rename()` so the operation is atomic
    on Windows as well as POSIX. `default=str` lets `decimal.Decimal` and
    other non-JSON-native types serialise without raising.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, default=str, indent=indent))
    tmp.replace(path)
