# Subsystem-grouping harness

A research harness for Layer 1. It parses a codebase, groups its files into subsystems, derives the
dependencies between those subsystems, and renders a static HTML report for a human to judge.

Background and decisions: [`docs/layer-1-codebase-map.md`](../../docs/layer-1-codebase-map.md).
Vocabulary: [`CONTEXT.md`](../../CONTEXT.md).

## Setup

Requires **Python 3.11+** (graphify needs ≥3.10).

```bash
python3.11 -m venv .venv
./.venv/bin/pip install graphifyy leidenalg igraph scipy scikit-learn networkx pandas anthropic pydantic
```

Naming subsystems calls the Anthropic API. Put a key in `.env` (git-ignored):

```
ANTHROPIC_API_KEY=sk-ant-...
```

Without a key the pipeline still runs; subsystems come out unnamed.

## Running

File selection is whatever `git ls-files` returns for the repo — the whole tree, respecting
`.gitignore`, narrowed by the extension filter. No target directories to pass.

```bash
./.venv/bin/python run.py                       # defaults to SpendWell
./.venv/bin/python run.py <repo_root>            # any repo
./.venv/bin/python run.py <repo_root> --exts .py  # override source extensions
```

The report lands in `out/report-<repo>.html`.

```bash
./.venv/bin/python run.py repos/hono
./.venv/bin/python run.py /Users/you/projects/centerpiece-api
```

Test repos are cloned into `repos/` (git-ignored). Clone blobless — the evolutionary signal reads git
history, so a shallow clone will silently weaken it:

```bash
git clone --filter=blob:none https://github.com/honojs/hono.git repos/hono
```

## Modules

The pipeline itself lives in `engine/` (repo root) — this harness imports it:

| Module | Does |
|---|---|
| `engine/extract.py` | `git ls-files` → tree-sitter AST via graphify → file graph (`{"A\|B": weight}`, A depends on B) |
| `engine/signals.py` | the three file-pair signals: structural, lexical, evolutionary |
| `engine/grouping.py` | Leiden — the grouping method in use |
| `engine/subsystem_graph.py` | quotients the file graph under a grouping → dependencies + crossings, graded major/minor (`share=0.15`, `cap=3`); triages isolated groups into islands vs noise |
| `engine/naming.py` | LLM names subsystems and layers, grounded in their files |
| `engine/map.py` | assembles the map document served by `server/app.py` |

This harness adds the research baselines and the report:

| Module | Does |
|---|---|
| `src/methods.py` | the baselines Leiden was judged against: `folders`, `hac`, `dsm` |
| `src/report.py` | static self-contained HTML |
| `run.py` | orchestrates the above |

Each engine module runs standalone as a smoke test, e.g. `./.venv/bin/python -m engine.subsystem_graph`
(run from the repo root, not this directory).

`methods.hac` is kept but not run — see the decisions in the Layer 1 document.

## Gotchas

- **graphify returns paths relative to the process CWD** when a file lives beneath it, and absolute
  paths otherwise. `engine/extract.py` normalizes both through `_abs()`. Getting this wrong drops every
  edge *silently* — you get zero dependencies and no error.
- **LLM naming must stream.** The SDK refuses non-streaming requests with a large `max_tokens`, and the
  budget scales with group count.
- **graphify caches ASTs** into `graphify-out/` (git-ignored). Delete it to force a re-parse.
