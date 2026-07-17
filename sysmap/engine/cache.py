"""Where the slow things are kept.

Parsing a repo takes seconds to minutes, so the AST cache and the map cache
both want to outlive a run. Neither belongs where it used to be: graphify was
handed `Path(".")`, which drops its cache into whatever directory you happened
to run from — someone else's repo, once this is a command — and the map cache
sat beside the code, which after an install means inside site-packages, a place
that is often read-only and always the wrong place to put a user's data.

Both go under one cache directory instead, the one the platform expects:
XDG_CACHE_HOME if it is set, ~/Library/Caches on macOS, ~/.cache otherwise.
The repo being mapped is never written to.

Keyed by the repo's full path, hashed. Two checkouts of the same project are
genuinely different maps — different commits, maybe different edits — so they
get different entries, and the name is kept on the front of the directory so
`ls ~/.cache/sysmap` is readable rather than a wall of hashes.
"""
from __future__ import annotations
import os
import sys
from hashlib import sha1
from pathlib import Path

APP = "sysmap"


def cache_home() -> Path:
    """The base directory for everything we keep between runs."""
    if xdg := os.environ.get("XDG_CACHE_HOME"):
        return Path(xdg) / APP
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / APP
    return Path.home() / ".cache" / APP


def repo_cache(root: Path) -> Path:
    """This repo's own corner of the cache, created if it isn't there.

    The path is resolved first: a repo reached through a symlink and the same
    repo reached directly are one repo, and should not be parsed twice.
    """
    root = root.resolve()
    key = sha1(str(root).encode()).hexdigest()[:8]
    d = cache_home() / f"{root.name}-{key}"
    d.mkdir(parents=True, exist_ok=True)
    return d
