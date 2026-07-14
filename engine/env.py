"""Minimal .env loader (no dependency) — reads KEY=VALUE lines into os.environ."""
from __future__ import annotations
import os
from pathlib import Path

_ENV = Path(__file__).resolve().parent.parent / ".env"


def load_env() -> None:
    if not _ENV.exists():
        return
    for line in _ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and val and key not in os.environ:
            os.environ[key] = val
