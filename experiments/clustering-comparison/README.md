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

```bash
./.venv/bin/python run.py                                          # defaults to SpendWell
./.venv/bin/python run.py <repo_root> <target_dir> [<target_dir>…] # any repo
./.venv/bin/python run.py <repo_root> <target_dir> --exts .py      # override source extensions
```

The report lands in `out/report-<repo>.html`.

```bash
./.venv/bin/python run.py repos/hono src
./.venv/bin/python run.py /Users/you/projects/centerpiece-api src
```

Test repos are cloned into `repos/` (git-ignored). Clone blobless — the evolutionary signal reads git
history, so a shallow clone will silently weaken it:

```bash
git clone --filter=blob:none https://github.com/honojs/hono.git repos/hono
```

## Modules

| Module | Does |
|---|---|
| `extract.py` | tree-sitter AST via graphify → file graph (`{"A|B": weight}`, A depends on B) |
| `signals.py` | the three file-pair signals: structural, lexical, evolutionary |
| `methods.py` | grouping methods: `folders` (baseline), `leiden` (in use), `hac`, `dsm` |
| `subsystem_graph.py` | quotients the file graph under a grouping → dependencies + crossings, graded major/minor (`share=0.15`, `cap=3`); triages isolated groups into islands vs noise |
| `naming.py` | LLM names subsystems and layers, grounded in their files |
| `report.py` | static self-contained HTML |
| `run.py` | orchestrates the above |

Each module runs standalone as a smoke test, e.g. `./.venv/bin/python -m src.subsystem_graph`.

`methods.hac` is kept but not run — see the decisions in the Layer 1 document.

## Gotchas

- **graphify returns paths relative to the process CWD** when a file lives beneath it, and absolute
  paths otherwise. `extract.py` normalizes both through `_abs()`. Getting this wrong drops every edge
  *silently* — you get zero dependencies and no error.
- **LLM naming must stream.** The SDK refuses non-streaming requests with a large `max_tokens`, and the
  budget scales with group count.
- **graphify caches ASTs** into `graphify-out/` (git-ignored). Delete it to force a re-parse.
