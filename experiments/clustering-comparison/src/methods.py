"""Phase 5 - the four grouping methods.

Each returns a dict describing its grouping so the report can render them uniformly.
"""
from __future__ import annotations
import os
from collections import defaultdict

import numpy as np
import networkx as nx
import igraph as ig
import leidenalg
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform


def _groups_to_list(labels, files):
    g = defaultdict(list)
    for f, lab in zip(files, labels):
        g[lab].append(f)
    return [sorted(v) for _, v in sorted(g.items(), key=lambda kv: -len(kv[1]))]


# --- 1. folders (baseline) -------------------------------------------------
def folders(files):
    labels = [os.path.dirname(f) for f in files]
    return {"name": "Folders (baseline)", "groups": _groups_to_list(labels, files)}


# --- 2. leiden (community detection) ---------------------------------------
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
            "groups": _groups_to_list(list(part.membership), files),
            "metric": f"modularity = {part.modularity:.3f}",
            "n_edges": len(edges)}


# --- 3. HAC (hierarchical) -------------------------------------------------
def hac(files, combined, k=None, method="ward"):
    dist = 1.0 - combined
    np.fill_diagonal(dist, 0.0)
    dist = (dist + dist.T) / 2
    Z = linkage(squareform(dist, checks=False), method=method)
    if k is None:
        k = max(3, round(len(files) ** 0.5))  # ~sqrt(n) groups
    labels = fcluster(Z, t=k, criterion="maxclust")
    # two extra zoom levels (coarser / finer) to show the hierarchy idea
    coarse = fcluster(Z, t=max(2, k // 2), criterion="maxclust")
    fine = fcluster(Z, t=min(len(files), k * 2), criterion="maxclust")
    return {"name": "HAC (hierarchical / dendrogram)",
            "groups": _groups_to_list(labels, files),
            "metric": f"cut at k={k} groups ({method} linkage)",
            "zoom": {"coarse": _groups_to_list(coarse, files),
                     "fine": _groups_to_list(fine, files)}}


# --- 4. DSM (layering) -----------------------------------------------------
def dsm(files, edges):
    """edges: dict 'A|B'->w meaning A depends on B (directed)."""
    D = nx.DiGraph()
    D.add_nodes_from(files)
    for key, w in edges.items():
        a, b = key.split("|")
        if a in D and b in D:
            D.add_edge(a, b, weight=w)
    # cycles = strongly connected components with >1 node
    sccs = [sorted(c) for c in nx.strongly_connected_components(D) if len(c) > 1]
    # layer via longest dependency chain on the DAG of SCCs
    cond = nx.condensation(D, scc=list(nx.strongly_connected_components(D)))
    depth = {}
    for node in nx.topological_sort(cond.reverse(copy=True)):
        succ = list(cond.successors(node))  # things this component depends on
        depth[node] = 0 if not succ else 1 + max(depth[s] for s in succ)
    layers = defaultdict(list)
    mapping = cond.graph["mapping"]  # file -> scc id
    comp_members = defaultdict(list)
    for f, cid in mapping.items():
        comp_members[cid].append(f)
    for cid, members in comp_members.items():
        layers[depth[cid]].extend(sorted(members))
    ordered = [sorted(layers[d]) for d in sorted(layers, reverse=True)]  # top -> bottom
    return {"name": "DSM (layering)",
            "layers": ordered,
            "cycles": sccs,
            "metric": f"{len(ordered)} layers, {len(sccs)} cycle(s)"}
