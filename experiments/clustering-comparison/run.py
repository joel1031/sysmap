"""Orchestrate the experiment: extract -> signals -> methods -> HTML report.

Leiden is the grouping method: across SpendWell/hono/documenso it kept 66-79% of
dependencies inside subsystems vs HAC's 26-52%, i.e. 2-6x fewer arrows to draw.
methods.hac() stays in methods.py - its dendrogram is the candidate for the
depth axis - but it no longer runs here.

Usage:
  python run.py                                    # defaults to SpendWell
  python run.py <repo_root> <target_dir> [...]     # any repo, one or more target subdirs
  python run.py <repo_root> <target_dir> --exts .py  # override the source extensions
"""
import sys
from pathlib import Path

from src.env import load_env
load_env()  # pull ANTHROPIC_API_KEY from .env before anything needs it

from src.extract import build_file_graph
from src.signals import build_signals
from src import methods
from src.subsystem_graph import build_subsystem_graph
from src.report import render

DEFAULT_ROOT = Path("/Users/joelacosta/projects/SpendWell")
DEFAULT_TARGETS = ["frontend/src", "backend/src"]
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)


def _is_baseline(m) -> bool:
    return m["name"].startswith("Folders")


def main(argv):
    argv = list(argv)
    exts = None
    if "--exts" in argv:
        i = argv.index("--exts")
        exts = {e if e.startswith(".") else f".{e}" for e in argv[i + 1].split(",")}
        del argv[i:i + 2]

    if len(argv) >= 2:
        root = Path(argv[1]).resolve()
        targets = [root / t for t in argv[2:]] or [root / "src"]
    else:
        root, targets = DEFAULT_ROOT, [DEFAULT_ROOT / t for t in DEFAULT_TARGETS]
    name = root.name

    print(f"repo: {root}  targets: {[str(t.relative_to(root)) for t in targets]}")
    print("[1/4] structural graph (graphify)…")
    g = build_file_graph(root, targets, exts=exts)
    files, edges = g["files"], g["edges"]
    print("      ", g["_diag"])

    print("[2/4] signals (structural + lexical + co-change)…")
    sig = build_signals(files, edges, root)
    combined = sig["combined"]

    print("[3/4] running methods…")
    results = [
        methods.folders(files),
        methods.leiden(files, edges, combined),
        methods.dsm(files, edges),
    ]
    for m in results:
        print(f"       - {m['name']}: {m.get('metric', '')}")

    print("[3b/4] subsystem graph (dependencies between subsystems)…")
    for m in results:
        if "groups" not in m or _is_baseline(m):
            continue
        sg = m["subsystem_graph"] = build_subsystem_graph(m["groups"], edges)
        inside = sg["intra_edges"] / max(len(edges), 1)
        majors = set(sg["majors"])
        kept = sum(len(sg["deps"][k]) for k in majors) / max(sg["n_crossings"], 1)
        cyc_after = sum(1 for i, j in sg["bidirectional"]
                        if (i, j) in majors and (j, i) in majors)
        print(f"       - {m['name']}: {sg['n_subsystems']} subsystems, "
              f"{len(sg['deps'])} dependencies, {sg['n_crossings']} crossings, "
              f"{len(sg['bidirectional'])} circular, {len(sg['isolated'])} isolated "
              f"({len(sg['islands'])} islands, {len(sg['noise'])} noise), "
              f"{inside:.0%} of edges kept inside")
        print(f"         backbone: {len(majors)}/{len(sg['deps'])} major, "
              f"{kept:.0%} of crossings kept, circular {len(sg['bidirectional'])} → {cyc_after}")

    # optional LLM naming (skipped if no API key). The Folders baseline is left
    # unnamed on purpose: it is the strawman, and a plausible name on a bad
    # grouping only makes it look credible.
    try:
        from src.naming import name_groups, name_layers
        for m in results:
            if _is_baseline(m):
                continue
            if "groups" in m:
                m["names"] = name_groups(m["groups"], name)
            elif "layers" in m:
                m["names"] = name_layers(m["layers"], name)
        print("       - LLM named the subsystems & layers ✓")
    except Exception as e:
        print(f"       - LLM naming skipped ({type(e).__name__}: {str(e)[:80]})")

    print("[4/4] rendering report…")
    meta = (f"{name} · {len(files)} files · {len(edges)} directed dependencies · "
            f"{sig['n_commits']} commits · signals: structural+lexical+co-change (equal)")
    out = render(results, meta, OUT / f"report-{name}.html")
    print(f"\nreport: {out}")


if __name__ == "__main__":
    main(sys.argv)
