"""The connection summary — one plain sentence on how two subsystems work together.

Built on demand when a connection is opened, streamed to the page, and cached.
Reads the references that cross (what the source files take from the target) as
the evidence, and states the working relationship they add up to. See the spec:
docs/superpowers/specs/2026-07-14-detail-panel-design.md.
"""
from __future__ import annotations
from typing import Iterator

import anthropic

from engine.naming import MODEL
from engine.voice import HOUSE_VOICE

_RANK = {"call": 0, "use": 1, "import": 2}
_MAX_REFS = 30  # keep the prompt to a handful of names, per the cost budget


def _dir_refs(direction: dict) -> list[tuple[str, str]]:
    """The named things this direction carries, deduped across its crossings,
    keeping the most telling kind per name (call > use > import)."""
    best: dict[str, str] = {}
    for cr in direction.get("crossings", []):
        for r in cr.get("references", []):
            cur = best.get(r["name"])
            if cur is None or _RANK[r["kind"]] < _RANK[cur]:
                best[r["name"]] = r["kind"]
    return sorted(best.items(), key=lambda kv: (_RANK[kv[1]], kv[0]))


def _fmt_refs(refs: list[tuple[str, str]]) -> str:
    if not refs:
        return "(module-level imports only, nothing named)"
    shown = ", ".join(f"{n} ({k})" for n, k in refs[:_MAX_REFS])
    if len(refs) > _MAX_REFS:
        shown += f", and {len(refs) - _MAX_REFS} more"
    return shown


def build_prompt(conn: dict, subs_by_id: dict[str, dict]) -> str:
    """The user message for one connection: the two subsystems and how they use
    each other, ending in the one-sentence ask."""
    def label(sid: str) -> str:
        s = subs_by_id.get(sid) or {}
        name = s.get("name") or "an unnamed subsystem"
        desc = s.get("description")
        return f"{name} ({desc})" if desc else name

    lines = []
    uses = []
    for d in conn["directions"]:
        lines.append(f"- {label(d['source'])} takes from {label(d['target'])}: "
                     f"{_fmt_refs(_dir_refs(d))}")
        uses.append(d)

    a, b = conn["subsystems"]
    mutual = len(conn["directions"]) > 1
    ask = ("In one sentence, describe how these two subsystems work together — "
           "what each relies on the other for."
           if mutual else
           "In one sentence, describe how these two subsystems work together — "
           "what the first relies on the second for.")
    return (
        f"Two subsystems in this codebase are connected: {label(a)} and {label(b)}.\n\n"
        f"How they use each other:\n" + "\n".join(lines) + "\n\n"
        + ask + " Say what the borrowed things are for, in plain language; name a "
        "specific one only if it clearly dominates. Ground the sentence only in "
        "what's shown above."
    )


def stream_summary(prompt: str) -> Iterator[str]:
    """Yield the sentence in text deltas as the model writes it."""
    client = anthropic.Anthropic()
    with client.messages.stream(
        model=MODEL,
        max_tokens=200,
        system=HOUSE_VOICE,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for delta in stream.text_stream:
            yield delta
