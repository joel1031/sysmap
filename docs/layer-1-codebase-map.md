# Layer 1 — The Codebase Map

Vocabulary in this document is defined in [`CONTEXT.md`](../CONTEXT.md). Product principles live in
[`CLAUDE.md`](../CLAUDE.md).

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

The map is deliberately *not* a force-directed rendering of the whole file graph. Rendering everything
at once is a layout choice, and it is the layout choice that produces a hairball. The map shows less,
in a considered order.

## The approach

Structure is decided by algorithms operating on the real wiring of the code. Language is supplied by an
LLM at the last mile, grounded strictly in the files of the thing it is naming. The model never decides
what belongs together — it labels what the algorithms found. This is the line that separates a grounded
tool from a plausible-sounding one.

### Pipeline

```
source files
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
   │
   ▼
static HTML report
```

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

**Hierarchical clustering is retained but not run.** Its dendrogram is a natural fit for the depth axis —
descending is just cutting the same tree lower. It lost the breadth contest; it may win the depth one.

**The folders baseline is left unnamed.** It exists to be beaten. Giving it a plausible LLM-generated name
only makes a bad grouping look credible.

## Technology

| Concern | Choice |
|---|---|
| AST parsing | [`graphify`](https://github.com/Graphify-Labs/graphify) (tree-sitter, 25 language grammars) |
| Graph algorithms | `networkx`, `leidenalg` + `igraph` |
| Clustering / vectors | `scipy`, `scikit-learn` |
| Naming | Anthropic API, structured output, streamed |
| Report | static self-contained HTML, no JS |

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

Correctness rests on one invariant, asserted every run: **every file edge is accounted for exactly
once** — either as a crossing that backs some dependency, or as an edge internal to a subsystem. Nothing
dropped, nothing double-counted. This is the guard against the failure mode that matters here, which is
silent: a resolver that quietly drops edges produces a *beautiful, empty, wrong* map rather than an error.

## Where Layer 1 stands

**Done.** File graph, three signals, grouping, the subsystem graph (dependencies + crossings), LLM naming
of subsystems and layers, and a static report — running against three codebases.

**Open.**

- **Dependency density.** A 1,917-file monorepo yielded 11 clean subsystems but 98 dependencies between
  them — 89% of all possible pairs. The method is not at fault; the codebase is genuinely that
  interconnected. A readable map needs dependency *filtering*, and that forces the deferred layout and
  cycle-resolution questions.
- **The depth axis.** Descending into a subsystem means re-running a grouping method on only its files.
  Unbuilt. The leaf of a descent is the code itself.
- **Multi-language support is a project, not a flag.** Non-TypeScript codebases need more than an
  extension filter: reference resolution differs per language, and the lexical signal's stopword list is
  currently TypeScript/React-specific. Half-fixing it would produce results that are quietly wrong.
- **Familiarity-based adaptivity.** Cognitive-load theory says a worked example helps a newcomer and
  becomes noise to an expert. The map should recede in parts of the codebase you already know.
