"""Phase 1 - Structural graph (file-level) via graphify's tree-sitter extractor.

graphify returns SYMBOL-level nodes/edges. We collapse to FILE-level:
  node  = a source file (relative to repo root)
  edge  = A depends-on B, weight = count of symbol edges A->B
Direction is preserved (needed for the DSM layering method).

Each edge also keeps its references — the named things A takes from B, and
where both ends sit (the line A uses it on, the line B defines it on). An
edge whose name isn't where graphify says it is gets dropped; see
really_there().
"""
from __future__ import annotations
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from graphify.extract import extract

# graphify relation -> our reference kind (see CONTEXT.md: Reference). Only these
# name a concrete thing in the target file; imports_from/contains do not.
KIND = {"calls": "call", "imports": "import", "references": "use"}
# When one name is used more than one way, keep the most telling: a call beats a
# bare use beats an import.
KIND_RANK = {"call": 0, "use": 1, "import": 2}

# --- id normalization ------------------------------------------------------
# graphify file id  : normalize(full path)                e.g. ..._button_tsx
# graphify symbol id: normalize(path-without-ext)+_sym    e.g. ..._button_button
_NON = re.compile(r"[^a-z0-9]+")


def norm(s: str) -> str:
    return _NON.sub("_", s.lower()).strip("_")


def _line(loc: str | None) -> int | None:
    """graphify writes a position as 'L58' (and in one spot, a bare '58')."""
    if not loc:
        return None
    s = str(loc).lstrip("L")
    return int(s) if s.isdigit() else None


def _abs(p: str | None) -> str | None:
    """graphify reports paths relative to the CWD when a file lives under it."""
    return None if p is None else str((Path.cwd() / p).resolve())


# The languages the engine has been measured on and reads well: C, Go, Java,
# Python, TypeScript/JS. See docs/language-support.md for what each was measured
# against and what was left out — a language is here because its edges were
# checked by eye, not because tree-sitter has a grammar for it.
CODE_EXT = {
    ".c", ".h",
    ".go",
    ".java",
    ".py",
    ".ts", ".tsx", ".js", ".jsx", ".mjs",
}


def tracked_files(repo_root: Path) -> list[Path]:
    """Every file git tracks in this repo, absolute. Respects .gitignore for
    free (node_modules, build output, etc. never appear because the repo
    itself already declared them junk) - no directory-walking, no ignore
    rules of our own to maintain."""
    out = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "-z"],
        capture_output=True, check=True,
    ).stdout
    return [repo_root / p for p in out.decode().split("\0") if p]


def build_file_graph(repo_root: Path, exts: set[str] | None = None):
    # Resolved once, here, so every path in this function is the same kind of
    # path. graphify's paths come back resolved via _abs(), and a repo reached
    # through a symlink (/tmp on macOS, a symlinked home) would otherwise never
    # match them — every edge dropped, no error, an empty map.
    repo_root = repo_root.resolve()
    exts = exts or CODE_EXT
    files = [f.resolve() for f in tracked_files(repo_root) if f.suffix in exts]

    res = extract(files, cache_root=Path("."), parallel=False)
    nodes, edges = res["nodes"], res["edges"]

    root = str(repo_root)

    def rel(p: str) -> str:
        return p[len(root):].lstrip("/") if p.startswith(root) else p

    # tier-1: symbol/file id -> source_file, straight from nodes
    node_file = {n["id"]: n["source_file"] for n in nodes}
    # readable name of a target node (a function/value/type), for references
    node_label = {n["id"]: n.get("label") for n in nodes}
    # where that thing is DEFINED — the far end of a reference
    node_line = {n["id"]: _line(n.get("source_location")) for n in nodes}
    # tier-2: exact file id (with extension) -> path
    file_id_map = {norm(str(f)): str(f) for f in files}
    # tier-3: ext-less file id -> path (longest-prefix fallback for symbol ids)
    noext = {}
    for f in files:
        noext[norm(str(f.with_suffix("")))] = str(f)
    noext_keys = sorted(noext, key=len, reverse=True)

    def resolve(eid: str) -> str | None:
        if eid in node_file:
            return node_file[eid]
        if eid in file_id_map:
            return file_id_map[eid]
        for k in noext_keys:
            if eid == k or eid.startswith(k + "_"):
                return noext[k]
        return None

    # graphify matches names case-insensitively, so `JSON.stringify` binds to a
    # type called `Json` and invents an edge between two unrelated files. A real
    # reference sits on the line graphify reports for it (give or take a line,
    # for a call spread over several) — if the name isn't there, the match is
    # wrong, and so is the edge resting on it.
    _lines: dict[str, list[str]] = {}

    def source_lines(path: str) -> list[str]:
        if path not in _lines:
            try:
                _lines[path] = Path(path).read_text(errors="ignore").splitlines()
            except OSError:
                _lines[path] = []
        return _lines[path]

    def really_there(path: str, name: str, line: int | None) -> bool:
        src = source_lines(path)
        if line is None or not src:
            return True  # nothing to check it against — take graphify's word
        bare = name.rstrip("()").lstrip(".")
        return any(bare in s for s in src[max(0, line - 3):line + 2])

    keep = {str(f) for f in files}
    weights: Counter = Counter()
    # per file-edge A->B, the named things A takes from B, each with both ends:
    # {name: {kind, line (where A uses it), def_line (where B defines it)}}
    refs: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    unresolved = fabricated = 0
    for e in edges:
        # edge['source_file'] is the importer file directly (reliable)
        a = _abs(e.get("source_file"))
        b = _abs(resolve(e["target"]))
        if a is None or b is None:
            unresolved += 1
            continue
        if a not in keep or b not in keep:
            continue  # e.g. import of a test file we excluded
        if a == b:
            continue
        ra, rb = rel(a), rel(b)
        kind = KIND.get(e.get("relation"))
        name = node_label.get(e["target"]) if kind else None
        line = _line(e.get("source_location"))
        if name and not really_there(a, name, line):
            fabricated += 1
            continue  # matched to the wrong file — the edge goes with it
        weights[(ra, rb)] += e.get("weight", 1.0)
        if name:
            cur = refs[(ra, rb)].get(name)
            if cur is None or KIND_RANK[kind] < KIND_RANK[cur["kind"]]:
                # one occurrence per name — the most telling one, and the line
                # it sits on. Its other uses are a count, and counts aren't
                # what makes this readable.
                refs[(ra, rb)][name] = {
                    "kind": kind,
                    "line": line,
                    "def_line": node_line.get(e["target"]),
                }

    def ref_list(named: dict[str, dict]) -> list[dict]:
        # calls first, then uses, then imports; alphabetical within a kind
        items = sorted(named.items(), key=lambda kv: (KIND_RANK[kv[1]["kind"]], kv[0]))
        return [{"name": n, **r} for n, r in items]

    file_list = sorted(rel(str(f)) for f in files)
    return {
        "files": file_list,
        "edges": {f"{a}|{b}": w for (a, b), w in weights.items()},  # directed A->B
        "references": {f"{a}|{b}": ref_list(d) for (a, b), d in refs.items()},
        "_diag": {
            "n_files": len(file_list),
            "n_symbol_nodes": len(nodes),
            "n_symbol_edges": len(edges),
            "n_file_edges": len(weights),
            "n_edges_with_refs": len(refs),
            "unresolved_endpoints": unresolved,
            "fabricated_refs": fabricated,
            "relations": dict(Counter(e.get("relation") for e in edges)),
        },
    }


if __name__ == "__main__":
    import json, sys

    # A repo to look at: the one named, or the one you're standing in.
    ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    g = build_file_graph(ROOT)
    out = Path(__file__).resolve().parents[2] / "out"
    out.mkdir(exist_ok=True)
    (out / "structural.json").write_text(json.dumps(g, indent=2))
    d = g["_diag"]
    print("=== structural graph (file-level) ===")
    for k, v in d.items():
        print(f"  {k}: {v}")
    print(f"  files: {len(g['files'])}, directed file-edges: {len(g['edges'])}")
    print("\nsample file-edges (A depends on B):")
    for k, w in list(g["edges"].items())[:10]:
        a, b = k.split("|")
        print(f"  {a}  ->  {b}   (w={w})")
