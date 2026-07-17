"""Phases 2-4 - the three signals, computed where the grouping will look.

A signal is evidence that two files belong together (see CONTEXT.md):
  S  structural  (one imports or calls the other)
  L  lexical     (they share vocabulary)
  C  co-change   (they change together in git history)
combined = wS*S + wL*L + wC*C   (default weights: 1/3 each)

Only pairs joined by a real structural edge are computed, because those are the
only pairs leiden() ever asks about. A square matrix answers 2N questions with
N² numbers: 3.2GB of arithmetic at ten thousand files, 80GB at fifty thousand,
all but a sliver of it discarded unread. The dense builders still exist for the
HAC baseline, which genuinely needs every pair — they live in the harness, with
the other research baselines.

Each signal is scaled by the largest value among the pairs computed, rather than
across every pair. For two of the three that is the same number: structural is
zero off its edges by construction, and the pair that changes together most
often turns out to also import (measured, 1.00x on hono). Vocabulary is the
exception — two files can share a lot of words without importing each other, so
its strongest pair isn't always an edge, and scaling to the edges amplifies it
about 12%. That moves a few files between subsystems: agreement 0.96 against the
dense path on hono, with the same 31 groups.

Chosen deliberately. Preserving the old scale exactly means finding the single
most-similar pair in the repo, which is an all-pairs question — the very thing
being removed — and anchoring a whole repo's vocabulary scale to one pair of
near-duplicate files is fragile anyway. It is the same reasoning depth already
uses when it rebuilds signals per subset rather than inheriting the repo's.
"""
from __future__ import annotations
import re
import subprocess
from itertools import combinations
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer

# TS/JS keywords + boilerplate we don't want dominating the vocabulary signal
STOP = set("""const let var function return import export from default class extends
implements interface type enum public private protected readonly static async await
if else for while switch case break continue new this super void null undefined true
false typeof instanceof in of as any string number boolean object void never unknown
require module exports get set constructor react useState useEffect props state""".split())

_TOK = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_SPLIT = re.compile(r"[_]+|(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _subwords(tok: str):
    for w in _SPLIT.split(tok):
        w = w.lower()
        if len(w) > 2 and w not in STOP:
            yield w


def _norm(d: dict) -> dict:
    """Scale to [0,1] by the strongest pair present."""
    hi = max(d.values(), default=0.0)
    return {k: v / hi for k, v in d.items()} if hi > 0 else {k: 0.0 for k in d}


def edge_pairs(files: list[str], edges: dict[str, float]) -> list[tuple[int, int]]:
    """The pairs the grouping will ask about: both ends known, undirected, no
    self-pairs. Everything else in an N×N matrix is a number nobody reads."""
    idx = {f: i for i, f in enumerate(files)}
    out = set()
    for key in edges:
        a, b = key.split("|")
        if a in idx and b in idx:
            i, j = sorted((idx[a], idx[b]))
            if i != j:
                out.add((i, j))
    return sorted(out)


# --- structural ------------------------------------------------------------
def structural_of(files, edges, pairs) -> dict:
    """The edge weights themselves, both directions summed (grouping has no
    direction; only dependencies do)."""
    idx = {f: i for i, f in enumerate(files)}
    want = set(pairs)
    S: dict[tuple[int, int], float] = {}
    for key, w in edges.items():
        a, b = key.split("|")
        if a not in idx or b not in idx:
            continue
        i, j = sorted((idx[a], idx[b]))
        if (i, j) in want:
            S[(i, j)] = S.get((i, j), 0.0) + float(w)
    return _norm(S)


# --- lexical ---------------------------------------------------------------
def vocabulary(files, repo_root: Path):
    """Each file's words, weighed by how rare they are across the repo.

    Returns the matrix and the word each column stands for. The words are kept
    rather than discarded because naming a subsystem without a model asks the
    same question this matrix answers — which words are common in these files
    and rare everywhere else — and reading every file twice to ask it twice
    would be the one expensive thing on the path a keyless run always takes.
    """
    docs = []
    for f in files:
        text = (repo_root / f).read_text(errors="ignore")
        docs.append(" ".join(w for t in _TOK.findall(text) for w in _subwords(t)))
    vec = TfidfVectorizer(token_pattern=r"[a-z][a-z0-9]+", min_df=1)
    return vec.fit_transform(docs).tocsr(), list(vec.get_feature_names_out())


def lexical_of(tfidf, pairs) -> dict:
    """Cosine over identifiers and comments, one sparse dot per pair.

    The vocabulary is fitted over every file — how rare a word is only means
    anything against the whole corpus — but the N² product is never formed.
    TfidfVectorizer L2-normalises its rows, so a dot IS the cosine.
    """
    L = {(i, j): float(tfidf[i].multiply(tfidf[j]).sum()) for i, j in pairs}
    return _norm(L)


# --- co-change -------------------------------------------------------------
def cochange_of(files, repo_root: Path, pairs, max_files=12):
    """How often two files change in the same commit.

    max_files: ignore sweeping commits (e.g. the initial import) that touch
    many files at once -- they create a uniform floor, not real coupling.
    """
    idx = {f: i for i, f in enumerate(files)}
    fileset = set(files)
    want = set(pairs)
    C: dict[tuple[int, int], float] = {}
    log = subprocess.run(
        ["git", "-C", str(repo_root), "log", "--name-only", "--pretty=format:%H"],
        capture_output=True, text=True,
    ).stdout
    commits, cur = [], []
    for line in log.splitlines():
        if line and "/" not in line and " " not in line and len(line) >= 20:
            if cur:
                commits.append(cur)
            cur = []
        elif line in fileset:
            cur.append(line)
    if cur:
        commits.append(cur)
    commits = [c for c in commits if 2 <= len(set(c)) <= max_files]
    for changed in commits:
        for a, b in combinations(sorted(set(changed)), 2):
            p = (idx[a], idx[b]) if idx[a] < idx[b] else (idx[b], idx[a])
            if p in want:
                C[p] = C.get(p, 0.0) + 1.0
    return _norm(C), len(commits)


# --- combine ---------------------------------------------------------------
def edge_signals(files, edges, repo_root: Path, weights=(1 / 3, 1 / 3, 1 / 3)):
    """{'combined': {(i,j): weight}} for every pair with a structural edge.

    'tfidf' and 'vocab' come back too — the grouping never reads them, but
    naming a subsystem without a model does.
    """
    pairs = edge_pairs(files, edges)
    S = structural_of(files, edges, pairs)
    tfidf, vocab = vocabulary(files, repo_root)
    L = lexical_of(tfidf, pairs)
    C, n_commits = cochange_of(files, repo_root, pairs)
    wS, wL, wC = weights
    combined = {p: wS * S.get(p, 0.0) + wL * L.get(p, 0.0) + wC * C.get(p, 0.0)
                for p in pairs}
    return {"S": S, "L": L, "C": C, "combined": combined, "tfidf": tfidf,
            "vocab": vocab, "files": files, "n_commits": n_commits,
            "n_pairs": len(pairs)}


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    from engine.extract import build_file_graph

    ROOT = Path("/Users/joelacosta/projects/SpendWell")
    g = build_file_graph(ROOT)
    sig = edge_signals(g["files"], g["edges"], ROOT)
    n = len(sig["files"])
    print(f"files: {n}  git commits touching them: {sig['n_commits']}")
    print(f"pairs computed: {sig['n_pairs']}  (a square matrix would be {n * n:,})")
    fi = {f: i for i, f in enumerate(sig["files"])}

    def probe(a, b):
        ia = ib = None
        for f in sig["files"]:
            if a in f:
                ia, na = fi[f], f
            if b in f:
                ib, nb = fi[f], f
        if ia is None or ib is None:
            return
        p = (min(ia, ib), max(ia, ib))
        if p not in sig["combined"]:
            print(f"  {na.split('/')[-1]:28} <-> {nb.split('/')[-1]:28} (no edge)")
            return
        print(f"  {na.split('/')[-1]:28} <-> {nb.split('/')[-1]:28} "
              f"S={sig['S'].get(p, 0):.2f} L={sig['L'].get(p, 0):.2f} "
              f"C={sig['C'].get(p, 0):.2f} comb={sig['combined'][p]:.2f}")

    print("\nsignal spot-checks (expect payments cluster high):")
    probe("lib/charge.ts", "lib/stripe.ts")
    probe("lib/charge.ts", "lib/donate.ts")
    probe("lib/processViolation.ts", "lib/charge.ts")
    probe("lib/plaid.ts", "lib/sync.ts")
    probe("components/Button.tsx", "lib/stripe.ts")  # expect low
