# The local process

Runs the pipeline on demand and serves the map document to the page. One endpoint. Background and
decisions: [`docs/layer-1-codebase-map.md`](../docs/layer-1-codebase-map.md).

## Running

Normally started for you by `bin/map`. To run it on its own:

```bash
cd .. # the repo root - graphify writes its AST cache relative to the CWD
experiments/clustering-comparison/.venv/bin/uvicorn server.app:app --port 8642
```

Needs the same `.venv` as the research harness (see its README for setup) and an `ANTHROPIC_API_KEY`
in a `.env` at the repo root — without one, subsystems come back unnamed.

## `GET /map?repo=<path>`

Runs `git ls-files` on `<path>` for the whole tracked tree, parses it, groups it, grades the
dependencies, names the subsystems, and returns the map document defined in `engine/map.py`.

Parsing a large repo takes minutes, so results are cached in `cache/` (git-ignored), keyed to the
repo's current commit. The same commit answers instantly; a new commit re-runs the pipeline.
`&refresh=true` forces a re-run regardless of the cache.
