# Map visual round 1 — design

Vocabulary per [`CONTEXT.md`](../../../CONTEXT.md). This round makes the map dark, fluid, and
selectable. Everything here was decided by looking at mockups side by side; the mockups live in
`.superpowers/brainstorm/` (git-ignored).

## What prompted it

The first drawn map (centerpiece-api) read as tangled and frozen:

- Lines could only leave a box at its bottom-center and enter at its top-center, so any line to a
  neighbor or upward looped absurdly and lines piled onto each other.
- Dragging was disabled — the map couldn't be nudged at all.
- The page was a white default with no designed mood.

## Decisions

**Rows stays; physics stays dead.** An Obsidian-style layout (boxes repel, connections pull) was
considered and rejected again, on cognitive-load grounds: it reshuffles every run (no spatial memory
forms) and throws away the one thing position currently encodes — dependency direction. Fluidity
comes from interaction, not from physics.

**Look: "Signal", dark by default, light behind a toggle.** Near-black background with a faint dot
grid; boxes are dark cards with vivid per-subsystem colored outlines and a soft glow; text bright.
Chosen over a softer blue-grey ("Dusk") and a warm charcoal ("Ember") by mockup comparison. Light
mode is the same structure re-colored, behind a header toggle; both palettes judged by eye during
the build.

**Lines attach where the boxes face each other.** Not fixed bottom→top ports. This is the fix for
both the looping and most of the overlap.

**Connections are uniform thickness and still at rest.** Thickness no longer encodes weight — every
line is the same width, drawn as a faint track. Weight moves into selection (see below), so the
information is one click away instead of always shouting.

**Direction is shown by flow, not arrowheads.** When a connection is active, small light pulses
drift along the line in the direction the dependency points. The motion is the arrowhead. A mutual
pair animates each of its two directions its own true way.

**Flow runs only when asked.** The resting map is still. Clicking a box animates its connections in
*both* directions — outgoing pulses toward what it leans on, incoming pulses from what leans on it.
(Outgoing-only was tried in a mockup and read as broken for boxes that are only leaned on.)
Clicking a connection animates just that connection. Clicking empty map returns everything to rest.

**Selection card, anchored at the click.** Clicking a box opens a small card next to the box itself
(not a corner or sidebar — the explanation appears where you're already looking, per the
integration principle in `CLAUDE.md`). The card shows exactly two things: the subsystem's
one-sentence description (already produced by the naming step, currently shown nowhere) and its
file count. Nothing else — relationships are already visible as flowing lines, and deeper facts
belong to the depth axis later. A box with no connections gets one extra line stating it's fully
self-contained; there is no other island treatment (no badge, ring, or reserved zone — mockups of
those read as alienating the box).

**Clicking a connection shows what backs it.** An anchored card with the direction(s), the crossing
count, and the crossing list (file → file). Load-bearing, not optional: with uniform thickness this
is the only place weight lives.

**Boxes are draggable; positions are session-only.** Lines follow live while dragging. Reload
recomputes the rows layout; remembering dragged positions is a separate, later decision.

**Icons on boxes.** Each subsystem gets a small symbol beside its name, chosen by the naming step
from a fixed set (Lucide names), carried in the map document (`icon` field already exists, always
null today). Implemented straight, no mockup round.

**Noise: a corner chip that toggles ghost boxes.** A quiet pill in a map corner ("5 unwired
files"). Clicking it toggles the noise files onto the map as faint dashed outlines along the bottom
edge; off by default. Chosen as a mix of two mockup options (chip alone / ghosts alone).

**Tuned by eye, not pre-decided:** pulse speed and spacing, glow strength, exact palettes, card
typography.

## Scope

- `web/` — nearly all of it: theme, box/line styling, attachment, flow animation, selection state,
  cards, dragging, chip + ghosts, toggle.
- `engine/naming.py` + `engine/map.py` — the naming step also picks an icon per subsystem and the
  map document carries it. No other engine change.
- No server change beyond whatever the icon field already flows through.

## Out of scope (unchanged commitments)

Depth descent, remembering dragged positions, packaging, multi-language, familiarity-based
adaptivity.

## How it's judged

By eye, via `bin/map`, against SpendWell, centerpiece-api, and documenso (the swarm test for flow
and the card test for long file lists), in both themes, in all states: at rest, box selected,
connection selected, dragging while flow runs, chip open with ghosts shown.
