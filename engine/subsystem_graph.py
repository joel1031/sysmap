"""The subsystem graph - dependencies between subsystems.

Sibling of extract.build_file_graph(), one altitude up. Given a grouping and the
file graph's directed edges, emit the graph whose nodes are subsystems and whose
edges are dependencies. Formally the quotient graph of the file graph under the
grouping (cf. nx.quotient_graph), but we keep the crossings so a dependency can
be drilled into.

  dependency  A -> B, weight = number of distinct crossings
  crossing    one file edge whose files sit in different subsystems

Only the structural signal produces dependencies; lexical and evolutionary
signals are symmetric and carry no direction. See CONTEXT.md.
"""
from __future__ import annotations
from collections import defaultdict


def build_subsystem_graph(groups: list[list[str]], edges: dict[str, float],
                          share: float = 0.15, cap: int = 3):
    """groups: subsystem index -> its files. edges: 'A|B' -> w, A depends on B.

    Every dependency is graded major or minor. Major = it carries >= `share` of
    the crossings leaving its source subsystem; the source's heaviest arrow is
    always major (floor); never more than `cap` majors per source. Outgoing only.
    The majors are the backbone - the arrows the map draws.
    """
    n = len(groups)
    owner = {f: i for i, g in enumerate(groups) for f in g}
    deps: dict[tuple[int, int], list[tuple[str, str]]] = defaultdict(list)
    intra_by_group = [0] * n
    unowned = 0

    for key in edges:
        a, b = key.split("|")
        i, j = owner.get(a), owner.get(b)
        if i is None or j is None:
            unowned += 1
        elif i == j:
            intra_by_group[i] += 1
        else:
            deps[(i, j)].append((a, b))

    intra = sum(intra_by_group)
    crossings = sum(len(v) for v in deps.values())
    assert crossings + intra + unowned == len(edges), (
        f"lost edges: {crossings} + {intra} + {unowned} != {len(edges)}")

    # Grade: rank each source's outgoing deps by weight; share-qualified deps
    # are a prefix of that ranking, so truncating at `cap` cannot skip one.
    by_src: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for (i, j), cr in deps.items():
        by_src[i].append((j, len(cr)))
    majors: set[tuple[int, int]] = set()
    for i, out in by_src.items():
        total = sum(w for _, w in out)
        ranked = sorted(out, key=lambda t: (-t[1], t[0]))
        for rank, (j, w) in enumerate(ranked[:cap]):
            if rank == 0 or w / total >= share:
                majors.add((i, j))
    assert majors <= set(deps), "major not backed by a dependency"

    touching = [0] * n   # crossings in or out of each subsystem
    minor_count = [0] * n
    for (i, j), cr in deps.items():
        touching[i] += len(cr)
        touching[j] += len(cr)
        if (i, j) not in majors:
            minor_count[i] += 1
            minor_count[j] += 1

    pairs = set(deps)
    isolated = [i for i in range(n) if not any(i in k for k in pairs)]
    return {
        "n_subsystems": n,
        "deps": {k: sorted(v) for k, v in deps.items()},
        "majors": sorted(majors),
        "minor_count": minor_count,
        "intra_edges": intra,
        "intra_by_group": intra_by_group,
        "self_containment": [
            intra_by_group[i] / (intra_by_group[i] + touching[i])
            if intra_by_group[i] + touching[i] else 1.0
            for i in range(n)],
        "unowned_edges": unowned,
        "n_crossings": crossings,
        "bidirectional": sorted({(i, j) for i, j in pairs if (j, i) in pairs and i < j}),
        "isolated": isolated,
        "islands": [i for i in isolated if intra_by_group[i] > 0],
        "noise": [i for i in isolated if intra_by_group[i] == 0],
    }


def _label(i, groups, names):
    nm = names.get(i) if names else None
    return f"[{i}] {nm.name if nm else f'subsystem {i}'} ({len(groups[i])} files)"


def describe(sg, groups, names=None, max_crossings=4) -> str:
    majors = set(sg["majors"])
    kept = sum(len(sg["deps"][k]) for k in majors)
    cyc_after = sum(1 for i, j in sg["bidirectional"]
                    if (i, j) in majors and (j, i) in majors)
    reachable = {i for k in majors for i in k}
    out = [f"subsystems: {sg['n_subsystems']}   dependencies: {len(sg['deps'])}   "
           f"crossings: {sg['n_crossings']}   bidirectional: {len(sg['bidirectional'])}   "
           f"isolated: {len(sg['isolated'])} "
           f"({len(sg['islands'])} islands, {len(sg['noise'])} noise)",
           f"invariant: {sg['n_crossings']} crossings + {sg['intra_edges']} intra + "
           f"{sg['unowned_edges']} unowned  ✓",
           f"backbone: {len(majors)} major of {len(sg['deps'])} dependencies, "
           f"keeping {kept}/{sg['n_crossings']} crossings "
           f"({kept / sg['n_crossings']:.0%})" if sg["n_crossings"] else
           "backbone: no crossings",
           f"circular pairs on backbone: {len(sg['bidirectional'])} → {cyc_after}   "
           f"subsystems on backbone: {len(reachable)}/{sg['n_subsystems']}"]

    by_src = defaultdict(list)
    for (i, j), cr in sg["deps"].items():
        by_src[i].append((j, cr))

    for i in range(sg["n_subsystems"]):
        out.append("")
        out.append(f"{_label(i, groups, names)}   "
                   f"self-contained: {sg['self_containment'][i]:.0%}   "
                   f"minors touching: {sg['minor_count'][i]}")
        if not by_src[i]:
            out.append("   (no outgoing dependencies)")
        for j, cr in sorted(by_src[i], key=lambda t: -len(t[1])):
            nm = names.get(j) if names else None
            tgt = nm.name if nm else f"subsystem {j}"
            grade = "major" if (i, j) in majors else "minor"
            cyc = "  ↔ circular" if (j, i) in sg["deps"] else ""
            out.append(f"   → [{j}] {tgt:<28} {len(cr):>3} crossings  {grade}{cyc}")
            for a, b in cr[:max_crossings]:
                out.append(f"        {a} → {b}")
            if len(cr) > max_crossings:
                out.append(f"        … {len(cr) - max_crossings} more")
    return "\n".join(out)


if __name__ == "__main__":
    import warnings
    from pathlib import Path

    warnings.filterwarnings("ignore")
    from engine.extract import build_file_graph
    from engine.signals import edge_signals
    from engine.grouping import leiden

    ROOT = Path("/Users/joelacosta/projects/SpendWell")
    g = build_file_graph(ROOT)
    sig = edge_signals(g["files"], g["edges"], ROOT)
    m = leiden(g["files"], g["edges"], sig["combined"])
    sg = build_subsystem_graph(m["groups"], g["edges"])
    print(f"\n=== subsystem graph ({m['name']}) ===")
    print(f"file graph: {len(g['files'])} files, {len(g['edges'])} edges")
    print(describe(sg, m["groups"]))
