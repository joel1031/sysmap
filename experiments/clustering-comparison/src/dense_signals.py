"""The signals as full N×N matrices — a research baseline, not the engine.

The engine computes each signal only for pairs joined by a structural edge,
because those are the only pairs Leiden asks about (see engine/signals.py).
HAC is the exception: it clusters on a distance between *every* pair, so it
needs the whole matrix. It lives here for the same reason folders and DSM do —
it lost the breadth contest, and the comparison should stay re-runnable.

Anything the engine ships uses engine.signals.edge_signals instead. If you find
yourself importing this from engine/ or server/, something has gone wrong.
"""
from __future__ import annotations
from itertools import combinations
from pathlib import Path
import subprocess

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from sysmap.engine.signals import _TOK, _subwords


def _minmax(M: np.ndarray) -> np.ndarray:
    M = M.copy().astype(float)
    np.fill_diagonal(M, 0.0)
    hi = M.max()
    return M / hi if hi > 0 else M


def structural_matrix(files: list[str], edges: dict[str, float]) -> np.ndarray:
    idx = {f: i for i, f in enumerate(files)}
    M = np.zeros((len(files), len(files)))
    for key, w in edges.items():
        a, b = key.split("|")
        if a in idx and b in idx:
            M[idx[a]][idx[b]] += w
            M[idx[b]][idx[a]] += w  # undirected for grouping
    return _minmax(M)


def lexical_matrix(files: list[str], repo_root: Path) -> np.ndarray:
    docs = []
    for f in files:
        text = (repo_root / f).read_text(errors="ignore")
        docs.append(" ".join(w for t in _TOK.findall(text) for w in _subwords(t)))
    tfidf = TfidfVectorizer(token_pattern=r"[a-z][a-z0-9]+", min_df=1).fit_transform(docs)
    sim = (tfidf @ tfidf.T).toarray()
    return _minmax(sim)


def cochange_matrix(files: list[str], repo_root: Path, max_files=12):
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


def combine(S, L, C, weights=(1 / 3, 1 / 3, 1 / 3)) -> np.ndarray:
    wS, wL, wC = weights
    return wS * S + wL * L + wC * C


def build_signals(files, edges, repo_root: Path, weights=(1 / 3, 1 / 3, 1 / 3)):
    """Every pair, as matrices. Costs 8·N² bytes each — fine for a baseline on a
    research-sized repo, fatal for anything the engine has to open."""
    S = structural_matrix(files, edges)
    L = lexical_matrix(files, repo_root)
    C, n_commits = cochange_matrix(files, repo_root)
    combined = combine(S, L, C, weights)
    return {"S": S, "L": L, "C": C, "combined": combined,
            "files": files, "n_commits": n_commits}
