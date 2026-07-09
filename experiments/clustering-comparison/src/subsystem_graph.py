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


def build_subsystem_graph(groups: list[list[str]], edges: dict[str, float]):
    """groups: subsystem index -> its files. edges: 'A|B' -> w, A depends on B."""
    owner = {f: i for i, g in enumerate(groups) for f in g}
    deps: dict[tuple[int, int], list[tuple[str, str]]] = defaultdict(list)
    intra = unowned = 0

    for key in edges:
        a, b = key.split("|")
        i, j = owner.get(a), owner.get(b)
        if i is None or j is None:
            unowned += 1
        elif i == j:
            intra += 1
        else:
            deps[(i, j)].append((a, b))

    crossings = sum(len(v) for v in deps.values())
    assert crossings + intra + unowned == len(edges), (
        f"lost edges: {crossings} + {intra} + {unowned} != {len(edges)}")

    pairs = set(deps)
    return {
        "n_subsystems": len(groups),
        "deps": {k: sorted(v) for k, v in deps.items()},
        "intra_edges": intra,
        "unowned_edges": unowned,
        "n_crossings": crossings,
        "bidirectional": sorted({(i, j) for i, j in pairs if (j, i) in pairs and i < j}),
        "isolated": [i for i in range(len(groups))
                     if not any(i in k for k in pairs)],
    }


def _label(i, groups, names):
    nm = names.get(i) if names else None
    return f"[{i}] {nm.name if nm else f'subsystem {i}'} ({len(groups[i])} files)"


def describe(sg, groups, names=None, max_crossings=4) -> str:
    out = [f"subsystems: {sg['n_subsystems']}   dependencies: {len(sg['deps'])}   "
           f"crossings: {sg['n_crossings']}   bidirectional: {len(sg['bidirectional'])}   "
           f"isolated: {len(sg['isolated'])}",
           f"invariant: {sg['n_crossings']} crossings + {sg['intra_edges']} intra + "
           f"{sg['unowned_edges']} unowned  ✓"]

    by_src = defaultdict(list)
    for (i, j), cr in sg["deps"].items():
        by_src[i].append((j, cr))

    for i in range(sg["n_subsystems"]):
        out.append("")
        out.append(_label(i, groups, names))
        if not by_src[i]:
            out.append("   (no outgoing dependencies)")
        for j, cr in sorted(by_src[i], key=lambda t: -len(t[1])):
            nm = names.get(j) if names else None
            tgt = nm.name if nm else f"subsystem {j}"
            cyc = "  ↔ circular" if (j, i) in sg["deps"] else ""
            out.append(f"   → [{j}] {tgt:<28} {len(cr):>3} crossings{cyc}")
            for a, b in cr[:max_crossings]:
                out.append(f"        {a} → {b}")
            if len(cr) > max_crossings:
                out.append(f"        … {len(cr) - max_crossings} more")
    return "\n".join(out)


if __name__ == "__main__":
    import warnings
    from pathlib import Path

    warnings.filterwarnings("ignore")
    from src.extract import build_file_graph
    from src.signals import build_signals
    from src import methods

    ROOT = Path("/Users/joelacosta/projects/SpendWell")
    g = build_file_graph(ROOT, [ROOT / "frontend/src", ROOT / "backend/src"])
    sig = build_signals(g["files"], g["edges"], ROOT)
    for m in (methods.leiden(g["files"], g["edges"], sig["combined"]),
              methods.hac(g["files"], sig["combined"])):
        sg = build_subsystem_graph(m["groups"], g["edges"])
        print(f"\n=== subsystem graph ({m['name']}) ===")
        print(f"file graph: {len(g['files'])} files, {len(g['edges'])} edges")
        print(describe(sg, m["groups"]))
