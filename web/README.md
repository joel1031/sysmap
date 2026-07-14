# The map

Draws the map document served by `server/` — boxes for subsystems, lines for their connections.
Vocabulary: [`CONTEXT.md`](../CONTEXT.md). Background and decisions: [`docs/layer-1-codebase-map.md`](../docs/layer-1-codebase-map.md).

## Running

Normally you don't run this directly — `bin/map`, run from inside the repo you want to see, starts
this alongside the local process and opens the browser for you.

To run it on its own (e.g. while iterating on how the page looks, with `server/` already running
separately):

```bash
npm install
npm run dev -- --port 5173
```

Then open `http://localhost:5173/?repo=/path/to/a/repo` — the page reads the repo to map from that
query parameter and fetches its map document from the local process on port 8642. There's no input
field for it in the page itself; the terminal command is the only entry point.

## Modules

| Module | Does |
|---|---|
| `App.tsx` | reads `?repo=` from the URL, fetches the map document, renders the header (theme toggle, re-map) and `MapView` |
| `api.ts` | `fetchMap()` — the one call to the local process's `/map` endpoint |
| `types.ts` | the map document's shape, as served by `engine/map.py` |
| `layout.ts` | positions every box — rows, via ELK, so major dependencies all point one direction |
| `MapView.tsx` | nodes, edges, selection state, the noise chip, and what's active when you click |
| `SubsystemBox.tsx` | a subsystem at rest: an icon and a name on a colored, sized card |
| `ConnectionEdge.tsx` | the drawn line — attaches where its boxes face each other; carries the flow pulses when active |
| `DetailCard.tsx` | the anchored card beside whatever you clicked — a box's description + file count, or a connection's crossings |
| `GhostBox.tsx` | one noise file as a faint dashed outline, toggled by the chip |

## Stack

React Flow draws the boxes and lines as real elements (not shapes on a canvas), which matters because
a box needs to become a designed card, not a rectangle with a label glued on. ELK computes the rows
layout. Vite compiles this TypeScript/React source into what a browser runs; during development it also
serves the page live with instant reload, which is why `bin/map` starts it rather than a one-time build.
lucide-react renders the box icons — the naming step picks each subsystem's icon by name from a fixed
list, and this package turns that name into the drawn symbol.
