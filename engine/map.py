"""Assemble the map document — the single artifact the browser reads.

The subsystem graph is data keyed by group index; the map document is that data
made drawable and addressable:
  - one entry per drawn subsystem (connected or island), with a stable id
  - one connection per pair of subsystems, carrying each direction's weight,
    grade, and crossings; the pair is on the backbone if any direction is major
  - the noise tray as a count and its group ids
  - the backbone figures

Stable ids are derived from a subsystem's file list, not its index, so a box
keeps its identity across runs as long as its membership doesn't change. The
chat and the agent will address boxes and connections by these ids later.
"""
from __future__ import annotations
import math
from hashlib import sha1


def _stable_id(files: list[str]) -> str:
    return sha1("\n".join(sorted(files)).encode()).hexdigest()[:8]


def _size_steps(counts: list[int]) -> list[int]:
    """Three size steps from this project's own spread of subsystem sizes.

    The spread can be huge (documenso: 2 to 371 files), so the two thresholds
    sit at the thirds of the range between the smallest and largest counts on
    a log scale, where a 2-vs-20 gap matters as much as a 30-vs-300 one.
    """
    lo, hi = math.log(min(counts)), math.log(max(counts))
    if hi - lo < 1e-9:
        return [2] * len(counts)
    t1, t2 = lo + (hi - lo) / 3, lo + 2 * (hi - lo) / 3
    return [1 + (math.log(c) > t1) + (math.log(c) > t2) for c in counts]


def build_map(repo_name: str, groups: list[list[str]], sg: dict, names=None) -> dict:
    names = names or {}
    majors = set(map(tuple, sg["majors"]))
    noise = set(sg["noise"])
    drawn = [i for i in range(sg["n_subsystems"]) if i not in noise]
    sid = {i: _stable_id(groups[i]) for i in range(sg["n_subsystems"])}
    steps = dict(zip(drawn, _size_steps([len(groups[i]) for i in drawn])))
    islands = set(sg["islands"])

    subsystems = []
    for i in drawn:
        nm = names.get(i)
        subsystems.append({
            "id": sid[i],
            "name": nm.name if nm else None,
            "description": nm.description if nm else None,
            "icon": nm.icon if nm else None,
            "files": groups[i],
            "size_step": steps[i],
            "self_containment": sg["self_containment"][i],
            "minor_count": sg["minor_count"][i],
            "island": i in islands,
        })

    by_pair: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for i, j in sg["deps"]:
        by_pair.setdefault((min(i, j), max(i, j)), []).append((i, j))
    connections = []
    for (a, b), dirs in sorted(by_pair.items()):
        directions = [{
            "source": sid[i], "target": sid[j],
            "weight": len(sg["deps"][(i, j)]),
            "grade": "major" if (i, j) in majors else "minor",
            "crossings": [{"from": x, "to": y} for x, y in sg["deps"][(i, j)]],
        } for i, j in sorted(dirs)]
        connections.append({
            "id": f"{sid[a]}~{sid[b]}",
            "subsystems": [sid[a], sid[b]],
            "on_backbone": any(d["grade"] == "major" for d in directions),
            "directions": directions,
        })

    kept = sum(len(sg["deps"][k]) for k in majors)
    circular_after = sum(1 for i, j in sg["bidirectional"]
                         if (i, j) in majors and (j, i) in majors)
    return {
        "repo": repo_name,
        "subsystems": subsystems,
        "connections": connections,
        "tray": {
            "count": len(sg["noise"]),
            "n_files": sum(len(groups[i]) for i in sg["noise"]),
            "group_ids": [sid[i] for i in sg["noise"]],
        },
        "backbone": {
            "majors": len(majors),
            "dependencies": len(sg["deps"]),
            "crossings_kept": kept,
            "n_crossings": sg["n_crossings"],
            "circular_before": len(sg["bidirectional"]),
            "circular_after": circular_after,
        },
    }


if __name__ == "__main__":
    import json
    import warnings
    from pathlib import Path

    warnings.filterwarnings("ignore")
    from engine.extract import build_file_graph
    from engine.signals import build_signals
    from engine.grouping import leiden
    from engine.subsystem_graph import build_subsystem_graph

    ROOT = Path("/Users/joelacosta/projects/SpendWell")
    g = build_file_graph(ROOT)
    sig = build_signals(g["files"], g["edges"], ROOT)
    m = leiden(g["files"], g["edges"], sig["combined"])
    sg = build_subsystem_graph(m["groups"], g["edges"])
    doc = build_map(ROOT.name, m["groups"], sg)
    print(json.dumps(doc, indent=2)[:2000])
    drawn_conn = [c for c in doc["connections"] if c["on_backbone"]]
    print(f"\n{len(doc['subsystems'])} subsystems, {len(drawn_conn)} backbone "
          f"connections of {len(doc['connections'])} pairs, "
          f"tray: {doc['tray']['count']} groups")
