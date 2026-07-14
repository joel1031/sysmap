"""Phases 2-4 - build the three signals and combine them.

signal matrices are all NxN over a fixed file index, values normalized to [0,1]:
  S  structural  (undirected: A->B and B->A summed)
  L  lexical     (TF-IDF cosine over identifiers + comments)
  C  co-change   (how often two files change together in git)
combined = wS*S + wL*L + wC*C   (default weights: 1/3 each)
distance = 1 - combined         (for HAC)
"""
from __future__ import annotations
import re
import subprocess
from itertools import combinations
from pathlib import Path

import numpy as np
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


def _minmax(M: np.ndarray) -> np.ndarray:
    M = M.copy().astype(float)
    np.fill_diagonal(M, 0.0)
    hi = M.max()
    return M / hi if hi > 0 else M


# --- structural ------------------------------------------------------------
def structural_matrix(files: list[str], edges: dict[str, float]) -> np.ndarray:
    idx = {f: i for i, f in enumerate(files)}
    M = np.zeros((len(files), len(files)))
    for key, w in edges.items():
        a, b = key.split("|")
        if a in idx and b in idx:
            M[idx[a]][idx[b]] += w
            M[idx[b]][idx[a]] += w  # undirected for grouping
    return _minmax(M)


# --- lexical ---------------------------------------------------------------
def lexical_matrix(files: list[str], repo_root: Path) -> np.ndarray:
    docs = []
    for f in files:
        text = (repo_root / f).read_text(errors="ignore")
        docs.append(" ".join(w for t in _TOK.findall(text) for w in _subwords(t)))
    tfidf = TfidfVectorizer(token_pattern=r"[a-z][a-z0-9]+", min_df=1).fit_transform(docs)
    sim = (tfidf @ tfidf.T).toarray()
    return _minmax(sim)


# --- co-change -------------------------------------------------------------
def cochange_matrix(files: list[str], repo_root: Path, max_files=12) -> np.ndarray:
    # max_files: ignore sweeping commits (e.g. the initial import) that touch
    # many files at once -- they create a uniform floor, not real coupling.
    idx = {f: i for i, f in enumerate(files)}
    fileset = set(files)
    M = np.zeros((len(files), len(files)))
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
        for a, b in combinations(set(changed), 2):
            M[idx[a]][idx[b]] += 1
            M[idx[b]][idx[a]] += 1
    return _minmax(M), len(commits)


# --- combine ---------------------------------------------------------------
def combine(S, L, C, weights=(1 / 3, 1 / 3, 1 / 3)) -> np.ndarray:
    wS, wL, wC = weights
    return wS * S + wL * L + wC * C


def build_signals(files, edges, repo_root: Path, weights=(1 / 3, 1 / 3, 1 / 3)):
    S = structural_matrix(files, edges)
    L = lexical_matrix(files, repo_root)
    C, n_commits = cochange_matrix(files, repo_root)
    combined = combine(S, L, C, weights)
    return {"S": S, "L": L, "C": C, "combined": combined,
            "files": files, "n_commits": n_commits}


if __name__ == "__main__":
    import json

    ROOT = Path("/Users/joelacosta/projects/SpendWell")
    out = Path(__file__).resolve().parent.parent / "out"
    g = json.loads((out / "structural.json").read_text())
    sig = build_signals(g["files"], g["edges"], ROOT)
    np.savez(out / "signals.npz", S=sig["S"], L=sig["L"], C=sig["C"],
             combined=sig["combined"], files=np.array(sig["files"]))
    print(f"files: {len(sig['files'])}  git commits touching them: {sig['n_commits']}")
    fi = {f: i for i, f in enumerate(sig["files"])}

    def probe(a, b):
        for f in sig["files"]:
            if a in f:
                ia = fi[f]; na = f
            if b in f:
                ib = fi[f]; nb = f
        print(f"  {na.split('/')[-1]:28} <-> {nb.split('/')[-1]:28} "
              f"S={sig['S'][ia][ib]:.2f} L={sig['L'][ia][ib]:.2f} C={sig['C'][ia][ib]:.2f} "
              f"comb={sig['combined'][ia][ib]:.2f}")

    print("signal spot-checks (expect payments cluster high):")
    probe("lib/charge.ts", "lib/stripe.ts")
    probe("lib/charge.ts", "lib/donate.ts")
    probe("lib/processViolation.ts", "lib/charge.ts")
    probe("lib/plaid.ts", "lib/sync.ts")
    probe("components/Button.tsx", "lib/stripe.ts")  # expect low
