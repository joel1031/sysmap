"""LLM cluster naming — the 'last mile' language layer.

The algorithms decide the STRUCTURE (which files group together). The LLM only
adds a human-readable NAME + one-line description to each group it's handed. It
never decides membership, so it can't invent structure — it labels what's there.

Grounded input = the file paths in each group (path carries dir + filename
signal). One API call names all groups at once so the model sees the whole
system and picks contrasting names.
"""
from __future__ import annotations
import os
from pydantic import BaseModel

import anthropic

from engine.voice import HOUSE_VOICE

MODEL = "claude-haiku-4-5-20251001"

# The fixed icon set the model picks from — Lucide icon names, kebab-case,
# exactly as the page's icon package spells them. Adding here is safe; the
# page falls back to no icon for a name it doesn't know.
ICONS = [
    "route", "database", "users", "mail", "shield", "settings", "file-text",
    "globe", "server", "layout-dashboard", "credit-card", "message-square",
    "image", "calendar", "search", "bell", "key", "lock", "wrench", "package",
    "layers", "git-branch", "book-open", "terminal", "code", "cloud", "zap",
    "truck", "shopping-cart", "receipt", "banknote", "table", "list-checks",
    "flask-conical", "pen-tool", "palette", "cpu", "hard-drive", "network",
    "workflow", "folder-open", "clipboard-list", "phone", "camera", "map",
    "house", "heart", "star", "tag", "funnel",
]


def _budget(n_groups: int) -> int:
    """~150 tokens per named group; 2000 truncated mid-JSON at 14 groups."""
    return max(2000, 200 * n_groups)


def _ask(prompt: str, n: int) -> dict[int, "GroupName"]:
    """Stream: the SDK refuses non-streaming calls with a large max_tokens."""
    client = anthropic.Anthropic()  # resolves ANTHROPIC_API_KEY / ant profile
    with client.messages.stream(
        model=MODEL,
        max_tokens=_budget(n),
        temperature=0,  # near-greedy: same groups tend to get the same names
        system=HOUSE_VOICE,
        messages=[{"role": "user", "content": prompt}],
        output_format=Naming,
    ) as stream:
        resp = stream.get_final_message()
    return {g.index: g for g in resp.parsed_output.groups}


class GroupName(BaseModel):
    index: int
    name: str          # 2-4 words, Title Case
    description: str    # one sentence, what this subsystem does
    icon: str           # one of ICONS, the subsystem's symbol on the map


class Naming(BaseModel):
    groups: list[GroupName]


def _render_groups(groups: list[list[str]]) -> str:
    lines = []
    for i, g in enumerate(groups):
        lines.append(f"Group {i} ({len(g)} files):")
        for f in g:
            lines.append(f"  {f}")
    return "\n".join(lines)


def name_groups(groups: list[list[str]], repo_name: str,
                parent: str | None = None) -> dict[int, GroupName]:
    """Return {index: GroupName}. Requires ANTHROPIC_API_KEY (or an ant profile).

    `parent` names the subsystem these groups were found *inside*, when this is
    a descent. It steers the names toward roles within that subsystem ("inside
    Payments, this piece is Refunds") instead of names that restate the parent.
    """
    where = (f"inside the '{parent}' subsystem of the '{repo_name}' codebase"
             if parent else f"in the '{repo_name}' codebase")
    scope = (
        f"Name each group by the part it plays WITHIN {parent}. Assume the reader "
        f"already knows they are looking inside {parent}, so do not restate it — "
        f"'Refunds', not '{parent} Refunds'.\n\n"
        if parent else
        "Name each group by its apparent responsibility in the system.\n\n"
    )
    prompt = (
        f"These are file clusters found {where} by a community-detection "
        f"algorithm run on its import/call graph. Each cluster is a candidate "
        f"subsystem. {scope}"
        f"Rules:\n"
        f"- name: 2-4 words, Title Case (e.g. 'Payments & Penalties', 'Bank Sync').\n"
        f"- description: one sentence on what this subsystem does.\n"
        f"- icon: the best-fitting symbol for this subsystem, chosen from exactly "
        f"this list (spell it identically): {', '.join(ICONS)}.\n"
        f"- Ground every name ONLY in the files shown. Do not invent components.\n"
        f"- Give every group a distinct name.\n\n"
        f"{_render_groups(groups)}"
    )
    return _ask(prompt, len(groups))


def name_layers(layers: list[list[str]], repo_name: str) -> dict[int, GroupName]:
    """Name architectural layers (index 0 = top tier, depends downward)."""
    body = []
    for i, lyr in enumerate(layers):
        pos = "TOP tier" if i == 0 else "BOTTOM tier" if i == len(layers) - 1 else "middle"
        body.append(f"Layer {i} ({pos}, {len(lyr)} files):")
        body.extend(f"  {f}" for f in lyr)
    prompt = (
        f"These are dependency LAYERS of the '{repo_name}' codebase, recovered by a "
        f"Dependency Structure Matrix. They form a vertical stack: layer 0 is the TOP "
        f"(entry points / high-level orchestration) and each layer depends DOWNWARD on "
        f"the ones below it; the bottom layer is leaf infrastructure that nothing else "
        f"depends out of.\n\n"
        f"Name each layer by its ARCHITECTURAL ROLE in that stack (e.g. 'Entry & Routing', "
        f"'Domain Services', 'Data & Infrastructure').\n\n"
        f"Rules:\n"
        f"- name: 2-4 words, Title Case.\n"
        f"- description: one sentence on this layer's role and what it sits on/above.\n"
        f"- icon: the best-fitting symbol from exactly this list (spell it "
        f"identically): {', '.join(ICONS)}.\n"
        f"- Ground every name ONLY in the files shown; give each layer a distinct name.\n\n"
        + "\n".join(body)
    )
    return _ask(prompt, len(layers))


if __name__ == "__main__":
    # smoke test on the current Leiden output
    from pathlib import Path
    import warnings
    warnings.filterwarnings("ignore")
    from engine.env import load_env
    load_env()
    from engine.extract import build_file_graph
    from engine.signals import edge_signals
    from engine.grouping import leiden

    ROOT = Path("/Users/joelacosta/projects/SpendWell")
    g = build_file_graph(ROOT)
    sig = edge_signals(g["files"], g["edges"], ROOT)
    L = leiden(g["files"], g["edges"], sig["combined"])
    names = name_groups(L["groups"], ROOT.name)
    for i, gr in enumerate(L["groups"]):
        n = names.get(i)
        print(f"\n[{n.name if n else '?'}] — {n.description if n else ''}")
        print("   " + ", ".join(f.split('/')[-1] for f in gr))
