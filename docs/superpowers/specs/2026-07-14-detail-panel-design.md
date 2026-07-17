# Detail Panel — design

## Context

The map answers *breadth*: which subsystems exist and how they relate. When a
developer selects something on it, the app has to explain that thing — and
today it explains poorly. A selected connection opens an anchored floating card
listing its crossings as raw file→file pairs; a selected box shows its name and
file count; a separate top-left strip carries the description. The file→file
list is a *measurement*, not an understanding ("25 files reach into 4"), and the
floating card is too small to ever hold the deeper information the tool exists
to present.

This replaces the card and the strip with one **permanent detail panel** docked
to the right of the map. The panel becomes the app's single, main surface for
deeper information about whatever is selected. It is designed from the start to
later hold Layer 1 *depth* (descending into a subsystem toward its code),
Layer 2 (decision support), and Layer 3 (agent orchestration) — so its shape is
chosen now to avoid a retrofit then.

North-Star discipline this design commits to: the panel *describes* structure
and lets the developer judge — it never hands out a health verdict, never leads
with counts, and never claims more than the evidence supports. Keeping the
developer doing the judging is the point.

## The panel, as a surface

- **Permanent and right-docked.** Open by default. It pushes the map narrower
  rather than covering it (the map is the working area beside a reference
  panel). On a narrow screen it flips to an overlay sheet so the map stays
  usable.
- **Closeable.** A clear **×** closes it for a clean, full-width map. Closing is
  never a trap: selecting any box or connection reopens it to that selection,
  and a slim tab on the right edge (a ‹ chevron) reopens it to whatever it last
  showed.
- **Flat, for now.** The panel reflects the current selection: a box shows the
  subsystem view, a connection shows the connection view, nothing selected shows
  a guiding message ("Select a subsystem or connection to explore how it fits").
  There is no in-panel drilling yet. When *depth* is built, the panel grows a
  navigable descent (breadcrumb + back), reachable from both the map and the
  panel; the flat layout is arranged so that navigation can sit on top without a
  redesign.
- **Replaces** the anchored detail card and the top-left description strip. Both
  fold into the panel and stop existing. Deselect/close is Esc, a click on empty
  map, or the ×.

## The connection view

Top to bottom:

1. **Header** — the two subsystems and the direction between them
   (`Insurance Operations → Asset Coverage`, or `⇄` for a mutual pair), with
   their icons and colors. The "where am I" line.
2. **The sentence** — one plain-English sentence describing *the whole
   relationship*, written by the model (see "The model call"). For a mutual
   pair it is a single sentence about how the two lean on each other, not one
   sentence per direction. It streams in live as it generates; once complete it
   is cached and re-opens instantly. While it streams, only this area shows
   motion — the header and crossings below are local and appear immediately, so
   the panel is never blank.
3. **What crosses** — the crossings, as rows of the two files that touch, each
   annotated with the references that cross — the things the source file takes
   from the target and how
   (e.g. `auth.ts → session.ts — calls createSession, imports verifyToken`).
   This is the concrete "where they touch." Rows look interactive; clicking a
   row to reveal the highlighted code is a **depth-phase** feature and is inert
   in this build.
4. **Reserved region for decision support (Layer 2)** — not built. The layout
   leaves an obvious place for it so Layer 2 slots in rather than forcing a
   redesign.

**Never shown:** crossing counts, dependency weight, or the major/minor grade —
anywhere in this view. They are measurements, not understanding.

## The subsystem view

Top to bottom:

1. **Header** — icon + name.
2. **Description** — the one sentence already generated at map-build time by
   naming. Subsystems already have a model-written sentence, so this view makes
   **no new model call**.
3. **Relationships** — two short lists: what this subsystem *reaches into* and
   what *reaches into it*, as subsystem names. Clicking one selects that
   connection (and the map re-focuses to it). This is breadth information,
   available now, stating the subsystem's role in the architecture in words.
4. **Reserved region for decision support (Layer 2)** — same deferred slot.

**Deferred to depth:** the file list and anything below it (that descent is
depth), and any metric such as self-containment.

## The model call

- **Trigger:** on demand, when a connection is opened for the first time. Never
  for boxes (they reuse their build-time description). Never precomputed for all
  connections.
- **Caching:** the final sentence is written into the existing per-commit cache
  file (`server/cache/*.json`, currently `{head, map}`) under a new
  per-connection map that fills in lazily. Same file, same invalidation — a new
  commit clears it.
- **Streaming:** the server already streams the naming call; the connection
  endpoint streams text deltas to the page, which types them into the sentence
  area. First open streams live; the completed text is saved to cache.
- **Input (the user message):** the two subsystems' names and descriptions, and
  the references that cross with their kinds (call / import / use), per
  direction. Not raw code.
- **Failure** (no credits / offline): the sentence area shows a plain "couldn't
  generate a summary" line; the rest of the panel still works.
- **Cost shape:** one build-time call (naming) + at most one per connection
  actually opened, cached thereafter. A fully-explored Deno API is
  ~21 calls *ever* for a commit; each connection call is a handful of reference
  names, not code.

## The house voice (shared system prompt)

Every model call the app makes — naming today, connection sentences now,
Layer 2 later — is given the same standing instructions as its `system`
parameter, so the app speaks in one voice and its principles live in one place.
The shared foundation is three parts:

1. **Role** — a guide that helps a developer understand the system they already
   own (not a generic summarizer).
2. **Voice** — plain English, active voice, calm and clear; the register of
   someone explaining your own code to you at a whiteboard.
3. **Guardrails** — no jargon, no counts or metrics, no good/bad verdict, no
   inventing purpose beyond the evidence.

Each specific call adds only its **task** and its **output shape**. For the
connection sentence: read the crossing references as evidence of how the two
subsystems couple, and state the working relationship they add up to, in one
sentence, staying strictly within the evidence.

Proposed sentence stance (to confirm at spec review): **abstracted to purpose**
— say what the borrowed references are *for* rather than listing identifiers,
naming a specific one only when it clearly dominates. The exact names still live
one layer down in the crossing rows, so nothing is lost. The actual house-voice
text is drafted during implementation and reviewed before it ships.

## The engine foundation

The model input and the crossing-row annotations both need the per-crossing
references the pipeline currently throws away. `engine/extract.py` collapses
graphify's finer edges to a file→file count; `subsystem_graph.py` carries only
the file pairs; `map.py` emits `{from, to}` per crossing. This design threads
the reference data through so each crossing carries the references that cross
and their kind.

Spike (done, on the React Native app): graphify's finer-grained nodes carry a clean,
correctly-cased name in their `label` field (`authMiddleware`, `plaidRoutes`,
`classify()`), and `imports` / `calls` / `references` edges point from the
importing file to the exact node, whose own `source_file` says which subsystem
it belongs to. So for a crossing A→B we can collect the names of B's things that
A calls, imports, or uses. The data is usable; we build on it with no fallback.

## Phasing

1. **Engine references.** Thread per-crossing references + kinds through
   `extract.py → subsystem_graph.py → map.py` into the map document and the
   page's types. Verify by re-mapping a repo and inspecting the document.
2. **House voice + connection endpoint.** Write the shared system prompt; apply
   it to the naming call too. Add the on-demand streaming endpoint that writes
   the connection sentence, backed by the per-commit sentence cache.
3. **Panel shell + views.** Build the permanent closeable panel (×, reopen tab,
   empty state, push/overlay), retire the card and strip, and build the flat
   connection and subsystem views consuming phases 1–2.

Later (depth phase, out of scope here): click-a-crossing → highlighted code, and
the in-panel drill navigation.

## What is deliberately deferred

- Click-a-crossing → code view (depth phase).
- In-panel drill-stack / breadcrumb navigation (depth phase).
- Decision support content — the reserved region stays empty (Layer 2).
- Subsystem file list and metrics (depth phase).

## Open questions

- Confirm the sentence stance (abstracted-to-purpose vs. always naming references).
- The exact house-voice prompt text — drafted in implementation, reviewed before
  it ships.
