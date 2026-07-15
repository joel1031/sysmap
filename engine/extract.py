"""Phase 1 - Structural graph (file-level) via graphify's tree-sitter extractor.

graphify returns SYMBOL-level nodes/edges. We collapse to FILE-level:
  node  = a source file (relative to repo root)
  edge  = A depends-on B, weight = count of symbol edges A->B
Direction is preserved (needed for the DSM layering method).
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


def _abs(p: str | None) -> str | None:
    """graphify reports paths relative to the CWD when a file lives under it."""
    return None if p is None else str((Path.cwd() / p).resolve())


CODE_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cts", ".mts"}


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
    exts = exts or CODE_EXT
    files = [f for f in tracked_files(repo_root) if f.suffix in exts]

    res = extract(files, cache_root=Path("."), parallel=False)
    nodes, edges = res["nodes"], res["edges"]

    root = str(repo_root)

    def rel(p: str) -> str:
        return p[len(root):].lstrip("/") if p.startswith(root) else p

    # tier-1: symbol/file id -> source_file, straight from nodes
    node_file = {n["id"]: n["source_file"] for n in nodes}
    # readable name of a target node (a function/value/type), for references
    node_label = {n["id"]: n.get("label") for n in nodes}
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

    keep = {str(f) for f in files}
    weights: Counter = Counter()
    # per file-edge A->B, the named things A takes from B: {name: kind}
    refs: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)
    unresolved = 0
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
        weights[(ra, rb)] += e.get("weight", 1.0)
        kind = KIND.get(e.get("relation"))
        name = node_label.get(e["target"]) if kind else None
        if name:
            cur = refs[(ra, rb)].get(name)
            if cur is None or KIND_RANK[kind] < KIND_RANK[cur]:
                refs[(ra, rb)][name] = kind

    def ref_list(named: dict[str, str]) -> list[dict[str, str]]:
        # calls first, then uses, then imports; alphabetical within a kind
        items = sorted(named.items(), key=lambda kv: (KIND_RANK[kv[1]], kv[0]))
        return [{"name": n, "kind": k} for n, k in items]

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
            "relations": dict(Counter(e.get("relation") for e in edges)),
        },
    }


if __name__ == "__main__":
    import json, sys

    ROOT = Path("/Users/joelacosta/projects/SpendWell")
    g = build_file_graph(ROOT)
    out = Path(__file__).resolve().parent.parent / "out"
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
