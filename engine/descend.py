"""One altitude down — the inside of a single subsystem.

Depth, per CONTEXT.md: movement down through one subsystem, into its
sub-modules, then its files, then its code. This module does the first part of
that — it takes one subsystem's files and runs the same pipeline on only them,
returning a map document of the same shape the top altitude uses. The page
draws it with the same code that draws the top map.

Two things make a descent different from the top-level run:

  - The signals are rebuilt over the subset, never sliced from the top-level
    matrix. build_signals scales each signal by the largest value it sees, and
    the vocabulary signal weighs a word by how rare it is across the files it
    is handed. Reuse the whole repo's numbers inside one subsystem and
    everything scores samey, with no contrast left for Leiden to split on —
    "payment" is a rare, telling word across the repo and noise inside
    Payments. Rebuilding rescales to this subsystem's own range and lets the
    words that are rare *here* do the work.

  - It has an outside. A subsystem's files reach files beyond it, and that
    wiring is what drew its arrows on the top map. Hiding it inside would make
    the inside a lie by omission, so those edges come back as `exits`.

The descent stops re-grouping when there is nothing meaningful left to split —
see FLOOR — and shows the files themselves.
"""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path

from engine.grouping import leiden
from engine.map import build_map
from engine.signals import build_signals
from engine.subsystem_graph import build_subsystem_graph

# Under this many files there is nothing worth splitting: a "subsystem" of four
# files is just four files. A starting guess, tuned by eye.
FLOOR = 8


def subset_edges(edges: dict[str, float], files: set[str]) -> dict[str, float]:
    """The wiring among these files only — both ends inside."""
    out = {}
    for key, w in edges.items():
        a, b = key.split("|")
        if a in files and b in files:
            out[key] = w
    return out


def _exits(edges: dict[str, float], inside: set[str], owner: dict[str, str],
           box_of: dict[str, str], labels: dict[str, dict]) -> list[dict]:
    """What the inside touches beyond itself.

    owner: file -> the id of the nearest box outside this one that holds it. A
    sibling where there is one, otherwise something higher up — so an exit
    points at the closest thing that means anything from where you're standing.
    box_of: file -> the id of the inner box holding it (this descent's own).

    Both directions: an outside subsystem this one reaches, and one that reaches
    into it. The top map draws a subsystem's arrows both ways, so an inside that
    owned up to only the outgoing half would be telling half the truth.
    """
    out: dict[str, set[str]] = defaultdict(set)  # outside id -> inner box ids
    into: dict[str, set[str]] = defaultdict(set)
    for key in edges:
        a, b = key.split("|")
        a_in, b_in = a in inside, b in inside
        if a_in == b_in:
            continue  # wholly inside, or wholly outside — neither is an exit
        if a_in and (o := owner.get(b)) and box_of.get(a):
            out[o].add(box_of[a])
        elif b_in and (o := owner.get(a)) and box_of.get(b):
            into[o].add(box_of[b])
    return [{"id": sid,
             "name": labels.get(sid, {}).get("name"),
             "icon": labels.get(sid, {}).get("icon"),
             # where it lives — always somewhere back up the way you came, so
             # the page can walk to it by trimming the trail it already has
             "path": labels.get(sid, {}).get("path", []),
             "out": sorted(out.get(sid, ())),
             "in": sorted(into.get(sid, ()))}
            for sid in sorted(set(out) | set(into))]


def descend(root: Path, graph: dict, files: list[str], parent: dict,
            owner: dict[str, str], labels: dict[str, dict],
            repo_name: str) -> dict:
    """The map document for the inside of one subsystem.

    graph: the cached file graph (files, edges, references) for the whole repo.
    files: the subsystem's files. parent: its entry from the map above.
    owner: file -> the id of the box outside this one that holds it.
    labels: id -> {name, icon, path}, to say what an exit leads to and where.
    """
    inside = set(files)
    edges = subset_edges(graph["edges"], inside)

    # Groups, unless there is nothing worth grouping. Leiden returning a single
    # group means it found no seam; forcing one would be inventing structure.
    floor = len(files) < FLOOR
    if not floor:
        sig = build_signals(files, edges, root)
        groups = leiden(files, edges, sig["combined"])["groups"]
        floor = len(groups) < 2
    if floor:
        groups = [[f] for f in sorted(files)]  # the files themselves

    sg = build_subsystem_graph(groups, edges)
    names = None
    if not floor:
        try:
            from engine.naming import name_groups
            names = name_groups(groups, repo_name, parent=parent.get("name"))
        except Exception:
            names = None

    doc = build_map(repo_name, groups, sg, names, graph.get("references"))
    box_of = {f: s["id"] for s in doc["subsystems"] for f in s["files"]}
    for f in (f for g in groups for f in g):
        box_of.setdefault(f, "")  # a file swept into the tray owns no box

    if floor:
        # A file names itself. No model call, no icon — it is not a subsystem.
        for s in doc["subsystems"]:
            path = s["files"][0]
            s["file"] = path
            s["name"] = path.split("/")[-1]
            s["description"] = path

    doc["parent"] = {k: parent.get(k) for k in ("id", "name", "description", "icon")}
    doc["floor"] = floor
    doc["exits"] = [e for e in _exits(graph["edges"], inside, owner, box_of, labels)
                    if e["id"] != parent.get("id")]
    return doc
