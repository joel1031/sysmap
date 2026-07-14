"""The grouping method — Leiden community detection.

Leiden is the engine's grouping method (decided 2026-07-08): across a 47x range
of codebase sizes it kept 66-79% of dependencies inside subsystems, i.e. the
fewest arrows the map has to draw. The research baselines (folders, HAC, DSM)
live in the harness, not here.
"""
from __future__ import annotations
from collections import defaultdict

import igraph as ig
import leidenalg


def groups_to_list(labels, files):
    g = defaultdict(list)
    for f, lab in zip(files, labels):
        g[lab].append(f)
    return [sorted(v) for _, v in sorted(g.items(), key=lambda kv: -len(kv[1]))]


def leiden(files, edges_dir, combined):
    # community detection runs on the SPARSE structural graph (real wiring),
    # with each real edge's weight enriched by the combined signal.
    n = len(files)
    idx = {f: i for i, f in enumerate(files)}
    pair_w = {}
    for key in edges_dir:
        a, b = key.split("|")
        if a in idx and b in idx:
            i, j = sorted((idx[a], idx[b]))
            pair_w[(i, j)] = max(pair_w.get((i, j), 0.0), float(combined[i][j]) + 0.05)
    edges = list(pair_w.keys())
    weights = [pair_w[e] for e in edges]
    G = ig.Graph(n=n, edges=edges)
    G.es["weight"] = weights
    part = leidenalg.find_partition(
        G, leidenalg.ModularityVertexPartition, weights="weight", seed=42)
    return {"name": "Leiden (community detection)",
            "groups": groups_to_list(list(part.membership), files),
            "metric": f"modularity = {part.modularity:.3f}",
            "n_edges": len(edges)}
