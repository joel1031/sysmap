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
from engine.signals import edge_signals
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


def _cache_file(root: Path, exts: str | None, kind: str = "") -> Path:
    """The map cache, and its two siblings.

    The file graph and the descents live beside the map rather than inside it:
    both the sentences and the descents are written back one entry at a time,
    and the graph is far the biggest of the four. Keeping them apart means
    caching one sentence doesn't rewrite a repo's whole edge list.
    """
    key = sha1("|".join([str(root), exts or ""]).encode()).hexdigest()[:8]
    return CACHE / f"{root.name}-{key}{kind}.json"


def _run_pipeline(root: Path, exts: set[str] | None) -> tuple[dict, dict]:
    """The map document, and the file graph it was built from.

    The graph is kept because the map document doesn't carry a subsystem's
    internal wiring — only the crossings between subsystems — and a descent
    needs exactly that, plus the edges leaving the subsystem for its exits.
    Caching it means descending never re-parses the repo.
    """
    g = build_file_graph(root, exts=exts)
    sig = edge_signals(g["files"], g["edges"], root)
    m = leiden(g["files"], g["edges"], sig["combined"])
    sg = build_subsystem_graph(m["groups"], g["edges"])
    try:
        from engine.naming import name_groups
        names = name_groups(m["groups"], root.name)
    except Exception:
        names = None
    return build_map(root.name, m["groups"], sg, names, g["references"]), g


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

    doc, graph = _run_pipeline(root, ext_set)
    cache_file.write_text(json.dumps({"head": head, "schema": SCHEMA, "map": doc}))
    _cache_file(root, exts, ".graph").write_text(
        json.dumps({"head": head, "schema": SCHEMA, "graph": graph}))
    _cache_file(root, exts, ".descents").unlink(missing_ok=True)  # a new map, new insides
    return doc


def _load(path: Path, head: str | None, what: str) -> dict:
    if not path.exists():
        raise HTTPException(404, f"{what} not built yet — re-map this repo")
    d = json.loads(path.read_text())
    if d.get("schema") != SCHEMA or (head and d.get("head") != head):
        raise HTTPException(409, f"{what} is stale — re-map this repo")
    return d


@app.get("/descend")
def get_descend(repo: str, path: str, exts: str | None = None,
                refresh: bool = False):
    """The inside of one subsystem — its files re-grouped into their own map.

    `path` is the altitude trail from the top map down, ids comma-separated:
    the last one is what you're opening, the ones before it say where you're
    standing. A subsystem is only addressable by the way you got to it, because
    its exits are described relative to that: from inside Onboarding Flow, the
    useful thing to say about a wire leaving it is that it lands in
    Authentication next door, not that it lands somewhere in Frontend Core.

    Each step down is computed the first time it's opened and cached from then
    on, so nobody pays for the insides of boxes they never look at.
    """
    root = Path(repo).expanduser().resolve()
    ids = [p for p in path.split(",") if p]
    if not ids:
        raise HTTPException(400, "path is empty")
    head = _head(root)
    doc = _load(_cache_file(root, exts), head, "map")["map"]

    dfile = _cache_file(root, exts, ".descents")
    descents = {}
    if dfile.exists():
        d = json.loads(dfile.read_text())
        if d.get("schema") == SCHEMA and d.get("head") == head:
            descents = d.get("descents", {})

    graph = None
    # file -> the box that holds it. Each altitude refines the one above, so by
    # the time we descend, a file's owner is the nearest box that isn't the one
    # being opened: a sibling where there is one, something higher up otherwise.
    owner = {f: s["id"] for s in doc["subsystems"] for f in s["files"]}

    def label_at(d: dict, at: list[str]) -> dict:
        return {s["id"]: {"name": s["name"], "icon": s["icon"], "path": at}
                for s in d["subsystems"]}

    labels = label_at(doc, [])

    for depth, sid in enumerate(ids):
        sub = next((s for s in doc["subsystems"] if s["id"] == sid), None)
        if sub is None:
            raise HTTPException(404, f"no such subsystem: {sid}")
        key = ",".join(ids[:depth + 1])
        last = depth == len(ids) - 1
        if key in descents and not (refresh and last):
            doc = descents[key]
        else:
            if graph is None:
                graph = _load(_cache_file(root, exts, ".graph"),
                              head, "file graph")["graph"]
            from engine.descend import descend
            doc = descend(root, graph, sub["files"], sub, owner, labels, root.name)
            descents[key] = doc
            dfile.write_text(json.dumps(
                {"head": head, "schema": SCHEMA, "descents": descents}))
        if not last:
            owner.update({f: s["id"] for s in doc["subsystems"] for f in s["files"]})
            labels.update(label_at(doc, ids[:depth + 1]))
    return doc


@app.get("/file", response_class=PlainTextResponse)
def get_file(repo: str, path: str, exts: str | None = None):
    """One source file, whole. The page windows it around the line it wants and
    keeps it, so reading several references in the same file costs one request.

    A path is served only if it is one of the files we actually parsed. That
    list is the tightest allowlist available and needs no reasoning about where
    a path resolves to: `../../../.ssh/id_rsa` is refused because it simply
    isn't in it. This server is local, which is not a reason to leave it open.
    """
    root = Path(repo).expanduser().resolve()
    head = _head(root)
    graph = _load(_cache_file(root, exts, ".graph"), head, "file graph")["graph"]
    if path not in set(graph["files"]):
        raise HTTPException(404, f"not a file in this map: {path}")
    try:
        return (root / path).read_text(errors="ignore")
    except OSError as exc:
        raise HTTPException(404, f"can't read {path}: {exc}")


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
