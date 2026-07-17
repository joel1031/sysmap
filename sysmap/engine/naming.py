"""Cluster naming — the 'last mile' language layer.

The algorithms decide the STRUCTURE (which files group together). Naming only
adds a human-readable NAME + description to each group it's handed. It never
decides membership, so it can't invent structure — it labels what's there.

Two ways to get a label, and the map draws the same either way:

  - With an API key, a model reads the file paths in each group and writes a
    name and a sentence. One call names every group at once, so it sees the
    whole system and picks contrasting names.

  - Without one, the group is named after its own words — the ones common in
    these files and rare across the repo, which is the question the vocabulary
    signal already answers on every run. No sentence: a description is prose,
    and nothing here understood the code well enough to write prose. The icon
    is a keyword match, which is a guess, but a cheap and visibly shallow one.

Naming after words rather than after the folder the files sit in is deliberate.
The grouping cuts across folders on purpose — that a subsystem doesn't match
the directory tree is usually the most interesting thing the map has to say —
so a folder-derived name would be most confidently wrong exactly where the map
is most worth reading.
"""
from __future__ import annotations
import sys
from dataclasses import dataclass
from pydantic import BaseModel

import anthropic

from sysmap.engine.voice import HOUSE_VOICE

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


# Words that suggest an icon, checked in order — the first row a group's words
# hit wins. A guess, and only ever reached when there is no key to do better.
WORD_ICON: list[tuple[tuple[str, ...], str]] = [
    (("auth", "login", "signin", "session", "oauth", "jwt", "permission"), "lock"),
    (("key", "secret", "crypto", "encrypt", "hash", "cipher", "signature"), "key"),
    (("pay", "payment", "charge", "stripe", "invoice", "billing", "refund",
      "donate", "checkout"), "credit-card"),
    (("bank", "balance", "ledger", "transaction", "plaid", "payout"), "banknote"),
    (("database", "sql", "query", "migration", "schema", "orm", "postgres",
      "sqlite", "mongo", "table"), "database"),
    (("cache", "redis", "storage", "bucket", "blob"), "hard-drive"),
    (("route", "router", "endpoint", "handler", "controller", "middleware"), "route"),
    (("http", "request", "response", "fetch", "url", "rest", "api"), "globe"),
    (("server", "daemon", "worker", "socket", "listener"), "server"),
    (("mail", "email", "smtp", "inbox"), "mail"),
    (("notify", "notification", "alert", "webhook"), "bell"),
    (("user", "profile", "member", "team", "account"), "users"),
    (("upload", "download", "file", "directory", "filesystem"), "file-text"),
    (("log", "logger", "trace", "telemetry", "metric"), "terminal"),
    (("config", "settings", "option", "env", "flag"), "settings"),
    (("test", "spec", "mock", "fixture", "assert", "stub"), "flask-conical"),
    (("sync", "job", "queue", "schedule", "cron", "worker", "pipeline"), "workflow"),
    (("component", "render", "view", "page", "css", "style", "layout",
      "button", "modal"), "layout-dashboard"),
    (("parse", "lexer", "ast", "compile", "grammar", "syntax"), "code"),
    (("error", "exception", "failure", "retry"), "shield"),
]
ICON_FALLBACK = "package"

# Words that are rare in a repo, common in a group, and still say nothing about
# what the group is FOR. Test scaffolding is the whole problem: a subsystem
# whose files have tests beside them scores 'mock' and 'stub' highly, and gets
# named after its tests instead of its job.
#
# Naming-only, deliberately. The grouping's own stop list (signals.STOP) feeds
# the vocabulary signal, so a word removed there changes which files group
# together — a map redrawn as a side effect of a naming tweak. These are
# dropped after the grouping has run and only from the words we name it with.
NAME_STOP = {
    "test", "tests", "spec", "mock", "mocks", "stub", "fake", "fixture",
    "expect", "assert", "describe", "beforeeach", "aftereach", "jest",
    "vitest", "pytest", "should", "todo", "index", "src", "lib", "util",
    "utils", "helper", "helpers", "common", "shared", "misc", "temp", "foo",
    "bar", "baz",
}


@dataclass
class Label:
    """What a keyless run knows about a group. Same three fields build_map reads
    off a GroupName, so the map is drawn by the same code either way."""
    name: str
    description: str | None
    icon: str | None


def have_key() -> bool:
    """Whether the SDK can find an API key.

    Asking the SDK rather than reading the environment ourselves: it looks in
    more places than one variable, and this way we never disagree with it about
    whether a key exists. It doesn't raise when there isn't one — it leaves
    api_key as None and fails much later, at request time.
    """
    try:
        return anthropic.Anthropic().api_key is not None
    except Exception:
        return False


def _top_words(tfidf, vocab: list[str], rows: list[int], k: int) -> list[str]:
    """The words this group of files is made of, strongest first.

    Summed across the group's rows, not averaged: a word in every file of the
    group beats a word used heavily in one and nowhere else, which is what
    naming a whole group ought to prefer.
    """
    import numpy as np

    if not rows:
        return []
    totals = np.asarray(tfidf[rows].sum(axis=0)).ravel()
    out = []
    for i in totals.argsort()[::-1]:
        if totals[i] <= 0:
            break  # sorted, so nothing below this scores either
        if vocab[i] not in NAME_STOP:
            out.append(vocab[i])
            if len(out) == k:
                break
    return out


def _icon_for(words: list[str]) -> str:
    for word in words:
        for keys, icon in WORD_ICON:
            if word in keys:
                return icon
    return ICON_FALLBACK


def words_for_groups(groups: list[list[str]], files: list[str], tfidf,
                     vocab: list[str]) -> dict[int, Label]:
    """Name each group after its own vocabulary. No key, no model, no network.

    Two words for the name — enough to tell subsystems apart, few enough to fit
    in a box — and a wider look for the icon, since the word that identifies a
    group and the word that suggests a picture of it are rarely the same one.
    """
    row = {f: i for i, f in enumerate(files)}
    out: dict[int, Label] = {}
    for i, group in enumerate(groups):
        rows = [row[f] for f in group if f in row]
        words = _top_words(tfidf, vocab, rows, k=8)
        name = " · ".join(words[:2]) if words else f"{len(group)} files"
        out[i] = Label(name=name, description=None, icon=_icon_for(words))
    return out


def label_groups(groups: list[list[str]], repo_name: str, sig: dict,
                 parent: str | None = None) -> tuple[dict[int, object], str]:
    """Label every group the best way available. Returns (labels, how).

    `how` is 'model' or 'words', so the caller can say which it got rather than
    leaving the reader to wonder why the names are terse.

    A key that is present but doesn't work falls back to words like any other
    run — a map is still worth drawing — but says so loudly. Silently treating
    a broken key as if no key were set is how a typo comes to look like a
    feature.
    """
    def words() -> dict[int, object]:
        return words_for_groups(groups, sig["files"], sig["tfidf"], sig["vocab"])

    if not have_key():
        return words(), "words"
    try:
        return name_groups(groups, repo_name, parent=parent), "model"
    except Exception as exc:
        print(f"naming: an API key is set but the call failed ({type(exc).__name__}: "
              f"{exc}). Naming these groups after their own words instead.",
              file=sys.stderr)
        return words(), "words"


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
    import sys
    from pathlib import Path
    import warnings
    warnings.filterwarnings("ignore")
    from sysmap.engine.env import load_env
    load_env()
    from sysmap.engine.extract import build_file_graph
    from sysmap.engine.signals import edge_signals
    from sysmap.engine.grouping import leiden

    ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    g = build_file_graph(ROOT)
    sig = edge_signals(g["files"], g["edges"], ROOT)
    L = leiden(g["files"], g["edges"], sig["combined"])
    names = name_groups(L["groups"], ROOT.name)
    for i, gr in enumerate(L["groups"]):
        n = names.get(i)
        print(f"\n[{n.name if n else '?'}] — {n.description if n else ''}")
        print("   " + ", ".join(f.split('/')[-1] for f in gr))
