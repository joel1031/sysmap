"""The local process — runs the pipeline on demand and serves the map document.

One endpoint for now: GET /map?repo=<path>. The chat and the agent are later
endpoints on the same process.

File selection is whatever `git ls-files` returns for the repo - the whole
tree, respecting .gitignore, narrowed by the extension filter. No target
directories to configure.

Parsing a large repo takes minutes, so results are cached per repo. The cache
remembers which commit the repo was on: same commit → instant answer, new
commit → the pipeline runs again. `refresh=true` forces a re-run regardless.

Run from the repo root (graphify writes its AST cache relative to the CWD):
  experiments/clustering-comparison/.venv/bin/uvicorn server.app:app
"""
from __future__ import annotations
import json
import subprocess
import sys
import warnings
from hashlib import sha1
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root, for engine/
warnings.filterwarnings("ignore")

from engine.env import load_env
load_env()  # ANTHROPIC_API_KEY for naming; without it subsystems come out unnamed

from engine.extract import build_file_graph
from engine.signals import build_signals
from engine.grouping import leiden
from engine.subsystem_graph import build_subsystem_graph
from engine.map import build_map

CACHE = Path(__file__).resolve().parent / "cache"
CACHE.mkdir(exist_ok=True)

# Bump when the map document's shape changes, so old cache entries are rebuilt
# rather than served stale. 2: crossings carry references. 3: references carry
# their call site and definition lines.
SCHEMA = 3

app = FastAPI(title="system-design map server")
app.add_middleware(  # the web dev server runs on its own port
    CORSMiddleware, allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["GET"], allow_headers=["*"])


def _head(root: Path) -> str | None:
    r = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def _cache_file(root: Path, exts: str | None) -> Path:
    key = sha1("|".join([str(root), exts or ""]).encode()).hexdigest()[:8]
    return CACHE / f"{root.name}-{key}.json"


def _run_pipeline(root: Path, exts: set[str] | None) -> dict:
    g = build_file_graph(root, exts=exts)
    sig = build_signals(g["files"], g["edges"], root)
    m = leiden(g["files"], g["edges"], sig["combined"])
    sg = build_subsystem_graph(m["groups"], g["edges"])
    try:
        from engine.naming import name_groups
        names = name_groups(m["groups"], root.name)
    except Exception:
        names = None
    return build_map(root.name, m["groups"], sg, names, g["references"])


@app.get("/map")
def get_map(repo: str, exts: str | None = None, refresh: bool = False):
    root = Path(repo).expanduser().resolve()
    if not root.is_dir():
        raise HTTPException(404, f"not a directory: {root}")
    ext_set = ({e if e.startswith(".") else f".{e}" for e in exts.split(",")}
               if exts else None)

    head = _head(root)
    cache_file = _cache_file(root, exts)
    if not refresh and head and cache_file.exists():
        cached = json.loads(cache_file.read_text())
        if cached["head"] == head and cached.get("schema") == SCHEMA:
            return cached["map"]

    doc = _run_pipeline(root, ext_set)
    cache_file.write_text(json.dumps({"head": head, "schema": SCHEMA, "map": doc}))
    return doc


@app.get("/connection")
def get_connection(repo: str, id: str, exts: str | None = None,
                   refresh: bool = False):
    """One plain sentence on how a connection's two subsystems work together,
    streamed as it generates and cached (per connection) in the map's cache
    file. Needs the map already cached — the page fetches it before any click."""
    root = Path(repo).expanduser().resolve()
    cache_file = _cache_file(root, exts)
    if not cache_file.exists():
        raise HTTPException(404, "map not built yet")
    cached = json.loads(cache_file.read_text())
    doc = cached["map"]
    conn = next((c for c in doc["connections"] if c["id"] == id), None)
    if conn is None:
        raise HTTPException(404, f"no such connection: {id}")

    sentences = cached.get("sentences", {})
    if not refresh and id in sentences:
        return PlainTextResponse(sentences[id])

    from engine.describe import build_prompt, stream_summary
    subs_by_id = {s["id"]: s for s in doc["subsystems"]}
    prompt = build_prompt(conn, subs_by_id)

    def gen():
        parts: list[str] = []
        try:
            for delta in stream_summary(prompt):
                parts.append(delta)
                yield delta
        except Exception as exc:  # no credits / offline: leave nothing cached
            print(f"connection summary failed: {exc}", file=sys.stderr)
            return
        text = "".join(parts).strip()
        if text:
            cached.setdefault("sentences", {})[id] = text
            cache_file.write_text(json.dumps(cached))

    return StreamingResponse(gen(), media_type="text/plain")
