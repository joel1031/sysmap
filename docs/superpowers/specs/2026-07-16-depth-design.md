# Depth — design

## Context

The map answers *breadth*: which subsystems exist and how they relate. The
detail panel explains whatever is selected. Neither goes **down**. A subsystem
named "Payments" with 40 files is, today, a box with a sentence — you cannot
look inside it, and you cannot reach the code that made the tool draw a line
between two boxes.

Depth is the last piece of Layer 1. CONTEXT.md defines it as *movement down
through one subsystem — into its sub-modules, then its files, then its code,
produced by re-running a grouping method on only that subsystem's files*, and
defines **altitude** as how far down you are: *the map shows subsystems at the
top altitude, code at the bottom*.

This spec builds that descent, and with it the deferred *click a crossing → see
the code* from the panel spec. When it lands, Layer 1 is complete.

North-Star discipline this design keeps: descending shows structure and code and
lets the developer judge. It does not grade, does not lead with counts, and does
not claim more than the evidence supports.

## The model: two axes that meet at code

Depth is not one movement. It is two, and they bottom out in the same place.

- **Box depth — the map redraws.** Descending into a subsystem replaces the
  canvas with that subsystem's own internal map: its files re-grouped into
  sub-subsystems, drawn as boxes with the connections among them. Keep going and
  you reach the **file nodes** themselves. The map is the altitude vehicle —
  CONTEXT.md says the map shows code at the bottom, so the map is what descends.
- **Connection depth — the panel deepens.** A connection is backed by crossings,
  a crossing by references, a reference by actual lines of code. Selecting a
  connection already shows the first two rungs; this spec adds the last one. The
  map does not redraw — there is no sub-map of a single connection.

Both end at **code**: a file opened from box depth, or the specific lines
highlighted from connection depth. Same surface, reached two ways.

The division of labour is the same at every altitude, including the floor: the
**map** answers *how do these relate*, the **panel** answers *what is this, show
me the code*.

## Descending

- **Trigger:** double-click a box, or an **Explore** button in the panel's
  subsystem view. The gesture is spatial; the button is discoverable. Single
  click still selects, as today.
- **What you land in:** the subsystem's internal map — sub-subsystems, the
  connections among them, and its exits (below). The panel keeps showing the
  subsystem you just entered; it is the subject until you click something more
  specific inside it, and its "Reaches into / Reached into by" list is the panel
  half of the exits.
- **The floor:** re-grouping stops when a subsystem is under **8 files** *or*
  Leiden returns a single group (it cannot meaningfully split). Then the map
  draws the **files themselves** as nodes, wired by the file→file edges among
  them. The threshold is a starting guess, to be tuned by eye.
- **Naming:** every altitude that produces groups gets named, exactly like the
  top map — one `name_groups` call per descent, with the parent subsystem's name
  passed as context ("inside Payments, this piece is Refunds"). Files are not
  named; a file names itself.

Because descent varies per branch, a small subsystem may bottom out in one step
and a large one take several. That is honest to the code.

## Exits

Inside subsystem A, some of A's files reach files outside A — that wiring is
what produced A's connections on the top map. Hiding it would make the inside a
lie by omission.

An **exit** is now a defined term — see CONTEXT.md.

Exits are shown **twice, deliberately**:
- **On the canvas** — one faint ghost marker per outside subsystem the inner
  pieces reach, labelled with that subsystem's name, wired to the inner boxes
  that reach it. Reuses the existing `ghost-box` style (dashed, faint) so real
  inner boxes stay dominant. Clicking a ghost climbs out and selects that
  subsystem.
- **In the panel** — the entered subsystem's relations list.

This puts *which inner piece owns each outward connection* in the picture, next
to the piece it belongs to.

## Navigation

Depth adds a second axis of return, and the panel already has the first
(selection history). Two separate "back" controls would be incoherent.

- **One unified history.** Every move — selecting a box, selecting a connection,
  descending, climbing — pushes one stack. **Back undoes the last move,
  whatever kind it was.** `App.tsx`'s `history` becomes a stack of
  `{altitude, sel}` rather than bare `Selection`.
- **A breadcrumb on the map** (`SpendWell › Payments › Refunds`) — orientation,
  and a jump to any altitude up the chain. It lives on the map area, not the
  panel: altitude is a property of the map; the panel is about the selection.

Back is *undo*; the breadcrumb is *where am I*. Different jobs, so they do not
compete.

## The code leaf

A reference carries both ends, and graphify already computes both — we were
discarding them:
- the **call site**: the line in the source file where A uses the thing
  (`source_location` on the edge, present on 100% of call edges spot-checked);
- the **definition**: the line in the target file where the thing is defined
  (`source_location` on the target node).

Clicking a reference shows **both**, call site first — a crossing *is* "A
reaches into B", so showing where A reaches next to what it reaches for is that
relationship made concrete in one view. This is the worked-example integration
CLAUDE.md argues for: the relationship, the reference, and the code together at
one point of attention rather than across tabs.

- **A window of ±8 lines** around each, headed by `path:line`, with the
  referenced line marked and an **expand** to the whole file. The window is the
  worked example; a whole file buries the line you came for, a single line
  strands you.
- **One line per reference.** A name used on several lines keeps the occurrence
  we already keep (the best-kind one). "How many times" is a count, and counts
  are not what makes this digestible. Additive later if wanted.
- **Colored by Shiki**, fine-grained (only the TS/JS-family grammars our
  `CODE_EXT` covers), themes `github-dark-default` / `github-light-default`, in
  dual-theme mode so its CSS variables switch off the `data-theme` attribute we
  already set on `<html>`. Shiki is the only option that serves both our themes
  without a hand-maintained second color set, and its real grammars color TSX
  correctly. Bundle cost to be **measured** before it is accepted; Prism is the
  fallback.
- **No model sentence at the file grain.** Between two files the references
  already *are* the story ("calls `formatDate`, imports `CURRENCY`") and the code
  is one click away. The house-voice sentence stays at the subsystem grain, where
  it earns its place compressing many crossings into one idea.

## Data

- **Computed on demand, cached per subsystem + commit** — the shape `/connection`
  already uses. Precomputing every altitude would multiply a minutes-long build
  by the branching factor to serve descents nobody opens.
- **The full file graph is cached** alongside the map. The map document only
  carries *crossings* (cross-boundary edges); a descent needs a subsystem's
  internal wiring, which is not in there, and exits need the edges pointing out.
  Caching the graph means a descent never re-parses.
- **Signals are recomputed on the subset**, not sliced from the top-level matrix.
  `build_signals` scales each signal by the largest value it sees, and the
  vocabulary signal weighs a word by how rare it is across the files it is given.
  Reusing the whole repo's numbers inside one subsystem leaves everything scoring
  samey, with no contrast for Leiden to split on — and "payment" is a rare,
  meaningful word across the repo but noise inside Payments. Recomputing rescales
  to the subsystem's own range and lets locally-rare words do the work.

## Edge cases

- **Islands** descend normally. Their inner map simply has no exit stubs.
- **Noise** does not descend — there is no wiring to re-group. But the tray's
  files become **clickable to their code**. Today the tray is a dead-end count,
  and CONTEXT.md is emphatic that *nothing is silently absent*; noise files are
  often live (config, framework entry points loaded by convention), so being able
  to read one is the right amount of access. No re-grouping, no naming, no model
  call.

## Phases

1. **References carry their location.** `extract.py` keeps the call-site and
   definition lines per reference. `SCHEMA` → 3.
2. **The descent.** Cache the file graph; new engine module; `GET /descend`
   returning an inner map — the same document shape as the top map, plus exits.
3. **The file endpoint.** `GET /file`, whole text, refusing any path not tracked
   by git inside that repo.
4. **Altitude on the map.** Descend, breadcrumb, unified history, exit stubs,
   file-node floor.
5. **The code leaf.** Shiki, the ±8 window, call site + definition, tray files.

Each phase stands alone. 1–3 are curl-able engine work; 4 and 5 are driven in a
real browser. **4 works without 5** (descend and explore before code exists) and
**5 works without 4** (a crossing's code opens from the top map today), so if
either page phase disappoints, the other still stands.

## What changed while building

- **A descent is addressed by its trail, not by an id** (`GET /descend?path=a,b`).
  Descending twice is the whole point of the floor rule, and an id alone can't
  express where you're standing — which also decides what an exit should say.
  From inside Onboarding Flow, the useful thing about a wire leaving it is that
  it lands in Authentication next door, not somewhere in Frontend Core. Each
  altitude on the way down refines who owns which file, so an exit names the
  nearest box outside rather than always jumping to the top.
- **Shiki loads on demand.** Measured at ~124kB gzipped — real enough that
  someone reading the map without opening a file shouldn't pay it. Behind a
  dynamic import, the map's own bundle grows 3kB (694→697kB gzip) and the
  grammars arrive with the first code view.
- **References are validated against their own line.** Carrying the lines
  exposed that graphify matches names case-insensitively, so `JSON.stringify`
  bound to a type called `Json` and invented a backend→frontend edge. A
  reference that isn't within a line or two of where it claims to sit is a bad
  match, and the edge under it goes too. Two of SpendWell's 127 file edges were
  fictional. Out of this spec's scope, agreed separately.

## What using it added

Three things the spec didn't call for, each found by driving the built thing:

- **A waiting surface over the map.** A descent takes seconds, and it was
  spending them showing the altitude you just left while the trail already
  claimed the new one — the page asserting a place it hadn't loaded. The old map
  now dims behind a surface that says what the wait is for. The same surface
  covers the first build and a re-map.
- **The panel's width is the reader's.** 360px was sized for a sentence and a
  list of crossings; the code leaf put code in there. The divider is draggable,
  clamped so the panel can't drop below a line of code or crowd out the map it
  exists to explain, and the width is remembered.
- **The map refits as the panel takes its space.** It was keeping its zoom and
  getting clipped at the edge, which reads as the map being cut off rather than
  making room. It now refits per frame — but only while the framing is still
  ours. Once the reader pans or zooms they have chosen a view, and overruling it
  on the next drag would be the tool overruling them.

## Status

Built, driven, and accepted (2026-07-16). **Layer 1 is complete**: the map goes
across at one altitude, down through a subsystem to its files, and into a
connection as far as the code on both ends of it.

## Unresolved

- The 8-file floor is still a guess. It behaves on SpendWell, which is small —
  it wants judging against a repo with subsystems big enough to descend two or
  three times.
- Subsystem naming still varies between runs even at temperature 0 — one
  descent named a box "User Profile" and the next "User Settings". Sampling is
  not the lever; seeding the grouping is.
