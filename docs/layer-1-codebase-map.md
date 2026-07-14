# Layer 1 — The Codebase Map

Vocabulary in this document is defined in [`CONTEXT.md`](../CONTEXT.md). Product principles live in
[`CLAUDE.md`](../CLAUDE.md).

# How to run:
Run `/Users/joelacosta/projects/system-design/bin/map` from any dir.

## Where Layer 1 sits

The product has three layers, and they stack:

1. **Codebase Map** — make the architecture of a codebase visible and navigable. *(this document)*
2. **Decision Support** — when you're about to build something, surface the relevant parts of the
   system and how similar decisions were made before.
3. **Agent Orchestration** — execute, constrained by the understanding built in layers 1 and 2.

Layers 2 and 3 are downstream of Layer 1 in a hard sense: you cannot surface "the relevant parts of
your system" until you can *identify* the parts. **Layer 1 is the dependency.** Everything the other
two layers promise rests on being able to answer one question about an arbitrary codebase:

> What are this system's subsystems, and how do they relate to each other?

## What Layer 1 has to produce

A **map**: a navigable picture explored along two axes.

- **Breadth** — how subsystems relate to their neighbours. The top-level view.
- **Depth** — descending into one subsystem: its sub-modules, then its files, then its code.

Breadth is built. Depth is not.

The map is deliberately *not* every file and every import drawn as its own dot and line. Rendering
everything at once produces a tangle no one can read. The map shows less, in a considered order.

## The approach

Structure is decided by algorithms operating on the real wiring of the code. Language is supplied by an
LLM at the last mile, grounded strictly in the files of the thing it is naming. The model never decides
what belongs together — it labels what the algorithms found. This is the line that separates a grounded
tool from a plausible-sounding one.

### Pipeline

```
source files (git ls-files, whole tracked tree)
   │  tree-sitter AST parsing (via graphify)
   ▼
file graph            directed: file A depends on file B
   │  three signals over file pairs
   ▼
structural · lexical · evolutionary
   │  a grouping method partitions the files
   ▼
groups  ──(named by LLM)──▶  subsystems
   │  quotient the file graph under the grouping
   ▼
subsystem graph       nodes = subsystems, edges = dependencies, each backed by crossings
   │  assembled into one document
   ▼
map document           connections (graded, on_backbone), size steps, the noise tray
   │  served by the local process (server/), cached by git commit
   ▼
the map                drawn by the page (web/), opened by `bin/map`
```

The research harness (`experiments/clustering-comparison/`) runs the same pipeline up through
the subsystem graph and renders it as a static HTML report instead — that's how methods and
parameters get judged before they reach the real map.

### Signals

Evidence that two files are related. Each answers a different question, and they are **not
interchangeable**:

| Signal | What it means | Symmetric? |
|---|---|---|
| **Structural** | one file imports or calls the other | no — has direction |
| **Lexical** | the two files share vocabulary (TF-IDF over identifiers and comments) | yes |
| **Evolutionary** | the two files change together in git history | yes |

Signals feed the grouping methods. Only the **structural** signal produces dependencies between
subsystems, because only it has direction — you cannot draw an arrow from a symmetric measurement.

## Decisions

**Leiden is the grouping method.** Community detection on the sparse structural graph, with each real
edge weighted by the blended signal. Chosen on evidence, not preference: across a 47× range of codebase
sizes it kept 66–79% of dependencies *inside* subsystems, where hierarchical clustering (Ward) kept
26–52%. The share of dependencies a method contains is the map's readability budget — every dependency
it fails to contain becomes an arrow someone has to look at.

**Run community detection on the sparse structural graph, never a dense similarity matrix.** Blending the
three signals into a dense file×file matrix and handing that to Leiden produced *negative* modularity —
worse than random. A graph where everything touches everything has no community structure to find.

**A dependency's weight is its number of distinct crossings.** Not the summed count of symbol references.
Summing conflates one file importing five symbols with five files importing one each, and it inflates
arrows pointing into large subsystems, so the map reports *size* as though it were *coupling*. A crossing
count is architecturally meaningful, and it is also the drill-in list.

**The subsystem graph carries no layering or cycle resolution.** Ordering subsystems vertically is a
*layout* concern, and it is impossible through a dependency loop. That decision waits until there is a
picture to lay out.

**Every dependency is graded major or minor; the map draws only the majors — the backbone.** A dependency
is major when it carries ≥ 15% (`share`) of the crossings leaving its source subsystem; the source's
heaviest arrow is always major (floor), and no source keeps more than 3 (`cap`). Outgoing only. Minors
stay in the graph and are reported as a per-subsystem count — nothing is silently absent. On the
documenso stress case this took 98 dependencies to 25 while keeping 61% of crossings and cutting mutual
pairs on the drawn map from 45 to 3. Rejected alternatives: the **disparity filter** (a 5-subsystem graph
has no degree distribution to be statistically significant against — it orphaned 2 of SpendWell's 5
subsystems); **top-N per source** (blind to weight); **both-ways share and incoming floors** (each
defeats the cap — documenso sources reached 9 and 6 majors against a cap of 3). The known tension: the
cap is outgoing-only, so a subsystem that is only *depended on* can drop off the backbone; the
per-subsystem minor count is the honesty mechanism, and the cap may need to grow with the subsystem
count — unresolved until a bigger map exists.

**Isolated groups are triaged by internal cohesion, not size.** No dependencies but real internal edges →
an *island*, drawn standing alone (documenso's 15-file docs site). No dependencies and no internal edges
→ noise, sent to a tray with a count. Verified not a resolver bug: the bulk of documenso's noise files
have zero edges because they are framework entry points (`next.config.mjs`, `robots.ts`, Remix routes)
loaded by path convention, not import.

**Every subsystem reports how self-contained it is** — the share of its edges that stay inside it. A
subsystem with 20 internal edges and 2 leaving still gets its strongest arrow drawn, because that arrow
is true; the self-containment figure tells the reader not to lean on it. Rejected the alternative of
grading an arrow against the subsystem's *total* traffic rather than its *outgoing* traffic: it silences
large cohesive subsystems (documenso's biggest would show no arrows at all despite sending out 588
crossings).

**Hierarchical clustering is retained but not run.** Its dendrogram is a natural fit for the depth axis —
descending is just cutting the same tree lower. It lost the breadth contest; it may win the depth one.

**The folders baseline is left unnamed.** It exists to be beaten. Giving it a plausible LLM-generated name
only makes a bad grouping look credible.

**File selection is `git ls-files`, not directory-walking.** The engine used to require a list of target
directories per repo, walked with graphify's own directory walker — which knows nothing about a repo's
`.gitignore`. `git ls-files` gives the whole tracked tree for free, respecting whatever the repo already
calls junk, narrowed by the existing code-extension filter. This also removed the last reason to exclude
test files, so they're no longer excluded. Verified on all four repos: SpendWell's boundaries stayed
clean with tests included (`charge.test.ts` sits right beside `charge.ts`); centerpiece-api and documenso
grew moderately in a way that reads as more honest, not smeared. hono fragmented more (9 → 20 drawn
subsystems) because of `benchmarks/` and `runtime-tests/` — whole parallel directories, not test files
beside source — but that's accepted as an honest reflection of that repo's actual shape rather than a
heuristic to filter around.

**Rows won the placement decision.** Two layouts were built behind a switch: rows (boxes stacked so major
dependencies all point one direction) and settle (boxes repelling, connections pulling like rubber bands,
no fixed meaning to position). Rendered SpendWell and hono in both and looked — rows read as the clearer
picture. Settle and its dependency (`d3-force`) were deleted; ELK is the only layout engine left. The
question was reopened once ("fluid, like Obsidian's graph view") and resolved the same way: a physics
layout reshuffles every run, so no spatial memory forms, and it throws away the one thing position
encodes — direction. Fluidity comes from interaction instead: boxes drag (session-only), lines follow.

**The map's look and behavior were decided by mockup comparison, not argument.** Recorded in full in
`docs/superpowers/specs/2026-07-13-map-visual-round-1-design.md`. The short version: dark by default
("Signal": near-black, vivid box outlines, soft glow) with a light toggle; connections are uniform faint
still lines that attach where their two boxes face each other; direction is shown by flow — light pulses
drifting the way the dependency points — and flow runs only when asked (click a box: every connection
touching it animates, both directions; click a connection: just that one). Weight moved off the line's
thickness into the connection's card, which lists the crossings behind the line. A box's card carries
only its one-sentence description and file count. Islands get no special treatment — a box with no lines
reads as alone on its own. Noise lives in a corner chip that toggles the files onto the map as faint
dashed ghosts.

## Technology

| Concern | Choice |
|---|---|
| AST parsing | [`graphify`](https://github.com/Graphify-Labs/graphify) (tree-sitter, 25 language grammars) |
| Graph algorithms | `networkx`, `leidenalg` + `igraph` |
| Clustering / vectors | `scipy`, `scikit-learn` |
| Naming | Anthropic API, structured output, streamed |
| Local process | FastAPI, one endpoint (`server/`) |
| The map | React + React Flow (boxes and lines as real elements, not a canvas), ELK (rows layout), Vite, lucide-react (the icon set the naming step picks from) (`web/`) |
| Harness report | static self-contained HTML, no JS — for judging the algorithm work, not the real map |

Graphify is reused rather than reimplemented because the hard part of building a file graph is not
parsing — tree-sitter does that per-file — but **resolving a reference in one file to a definition in
another** across path aliases, barrel files, and re-exports.

## How it's tested

The harness lives in `experiments/clustering-comparison/`. It runs the pipeline end to end against real
codebases and renders a report for a human to judge. The central question — *what is a subsystem* — is
answered **empirically, by looking at the output**, not by argument.

Test codebases, chosen to span size and shape:

| Repo | Files | Shape |
|---|---|---|
| SpendWell | 41 | React Native + Node app |
| centerpiece-api | 151 | Deno API service |
| hono | 186 | web framework |
| documenso | 1,917 | full-stack app — the stress case, ~10× the next-largest repo |

Correctness rests on one invariant, asserted every run: **every file edge is accounted for exactly
once** — either as a crossing that backs some dependency, or as an edge internal to a subsystem. Nothing
dropped, nothing double-counted. This is the guard against the failure mode that matters here, which is
silent: a resolver that quietly drops edges produces a *beautiful, empty, wrong* map rather than an error.

## Where Layer 1 stands

**Done.** File graph (whole tracked tree via `git ls-files`), three signals, grouping, the subsystem
graph (dependencies + crossings), dependency grading (major/minor, backbone, islands, noise), LLM naming
of subsystems and layers (name, description, icon), and the map document — served by a local process
(`server/`) and drawn as a picture (`web/`), opened with one terminal command (`bin/map`) that resolves
the repo from wherever it's run. The map's first visual round is built: the dark Signal look with a
light toggle, face-to-face line attachment, flow-on-click in both directions, anchored cards for boxes
and connections, dragging, icons, and the noise chip with ghosts. The research harness's static HTML
report still exists as the tool for judging the algorithm work itself.

**Open.**

- **The depth axis.** Descending into a subsystem means re-running a grouping method on only its files.
  Unbuilt. The leaf of a descent is the code itself.
- **Multi-language support is a project, not a flag.** Non-TypeScript codebases need more than an
  extension filter: reference resolution differs per language, and the lexical signal's stopword list is
  currently TypeScript/React-specific. Half-fixing it would produce results that are quietly wrong.
- **Familiarity-based adaptivity.** Cognitive-load theory says a worked example helps a newcomer and
  becomes noise to an expert. The map should recede in parts of the codebase you already know.
- **Packaging.** `bin/map` is the dev-time shape of a terminal command; installing it for someone who
  isn't you (a real package, a compiled page with no Node/npm dependency at install time, a story for
  where the Anthropic API key for naming comes from) is deliberately deferred until the visuals are
  settled.
