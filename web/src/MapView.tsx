import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Background,
  Controls,
  Panel,
  ReactFlow,
  applyNodeChanges,
  useReactFlow,
} from '@xyflow/react';
import type { Edge, Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { MapDocument } from './types';
import { exitId, place } from './layout';
import type { Positions } from './layout';
import { SubsystemBox } from './SubsystemBox';
import { GhostBox } from './GhostBox';
import { ExitBox } from './ExitBox';
import { ConnectionEdge } from './ConnectionEdge';
import type { Flow } from './ConnectionEdge';

// What's picked right now: a box, a connection, a file out of the tray, or
// nothing. Picking a box animates every connection touching it, in each
// dependency's true direction; picking a connection animates just that one.
// A file's id is its path — it has no box to be.
export type Selection =
  | { kind: 'box'; id: string }
  | { kind: 'connection'; id: string }
  | { kind: 'file'; id: string }
  | null;

// Vivid enough to read as outlines on near-black, mid enough for light mode.
const PALETTE = [
  '#5c7cfa', '#22c1a3', '#e8a33d', '#e05f8a', '#9a6dd7', '#38b6d9',
  '#a3b845', '#e07a4f', '#5fa87a', '#c46a9e', '#8a93ad', '#d9b96a',
  '#5f9ea0',
];

const nodeTypes = { subsystem: SubsystemBox, ghost: GhostBox, exit: ExitBox };
const edgeTypes = { connection: ConnectionEdge };

function buildNodes(doc: MapDocument, pos: Positions): Node[] {
  return doc.subsystems.map((s, i) => ({
    id: s.id,
    type: 'subsystem',
    position: pos[s.id] ?? { x: 0, y: 0 },
    data: {
      label: s.name ?? `subsystem ${i}`,
      color: PALETTE[i % PALETTE.length],
      sizeStep: s.size_step,
      icon: s.icon,
      // At the bottom of a descent a box is one file, not a group of them.
      file: s.file,
    },
  }));
}

// The subsystems this one touches from the outside, drawn at the edges of its
// map. Not subsystems of this map — doors out of it.
function buildExits(doc: MapDocument, pos: Positions): Node[] {
  return (doc.exits ?? []).map((e) => ({
    id: exitId(e.id),
    type: 'exit',
    position: pos[exitId(e.id)] ?? { x: 0, y: 0 },
    draggable: false,
    data: { label: e.name ?? 'elsewhere', icon: e.icon, target: e.id, depth: e.path.length },
  }));
}

function buildExitEdges(doc: MapDocument, sel: Selection): Edge[] {
  const out: Edge[] = [];
  for (const e of doc.exits ?? []) {
    const wire = (from: string, to: string, key: string, box: string) => {
      const active = sel?.kind === 'box' && sel.id === box;
      out.push({
        id: key,
        source: from,
        target: to,
        type: 'connection',
        className: `is-exit${sel === null ? '' : active ? ' is-focus' : ' is-dim'}`,
        selectable: false,
        data: { flows: [] },
      });
    };
    for (const b of e.out) wire(b, exitId(e.id), `xo-${e.id}-${b}`, b);
    for (const b of e.in) wire(exitId(e.id), b, `xi-${e.id}-${b}`, b);
  }
  return out;
}

// One line per pair: the connection. Uniform thickness, no arrowheads — the
// weight lives in the connection's detail card, and direction is shown by
// flow when the connection is active.
function buildEdges(
  doc: MapDocument,
  sel: Selection,
  colorOf: (sid: string) => string,
): Edge[] {
  return doc.connections
    .filter((c) => c.on_backbone)
    .map((c) => {
      const drawn = c.directions.find((d) => d.grade === 'major') ?? c.directions[0];
      const active =
        sel !== null &&
        ((sel.kind === 'connection' && sel.id === c.id) ||
          (sel.kind === 'box' && c.subsystems.includes(sel.id)));
      // Only major directions flow — the line only claims to draw the
      // backbone, so a minor back-direction must not pulse (it still shows
      // in the connection's card). Mutual majors animate both true ways.
      const flows: Flow[] = active
        ? c.directions
            .filter((d) => d.grade === 'major')
            .map((d) => ({
              color: colorOf(d.source),
              reverse: d.source !== drawn.source,
            }))
        : [];
      // At rest every line recedes equally. Once something's picked, the
      // lines touching it come forward and the rest fall further back — so
      // the shape you're tracing lifts out of the tangle.
      const className =
        sel === null ? undefined : active ? 'is-focus' : 'is-dim';
      return {
        id: c.id,
        source: drawn.source,
        target: drawn.target,
        type: 'connection',
        className,
        data: { flows },
      };
    });
}

// The noise files, laid out as rows of ghosts a little below the map.
function buildGhosts(doc: MapDocument, pos: Positions): Node[] {
  const files = doc.tray.files ?? [];
  const placed = Object.values(pos);
  if (!files.length || !placed.length) return [];
  const minX = Math.min(...placed.map((p) => p.x));
  const maxY = Math.max(...placed.map((p) => p.y));
  let x = minX;
  let y = maxY + 160;
  return files.map((f, i) => {
    const label = f.split('/').pop() ?? f;
    const w = 26 + label.length * 6.2;
    if (x + w > minX + 940) {
      x = minX;
      y += 40;
    }
    const node: Node = {
      id: `ghost-${i}`,
      type: 'ghost',
      position: { x, y },
      draggable: false,
      data: { label, full: f },
    };
    x += w + 10;
    return node;
  });
}

export function MapView({
  doc,
  theme,
  sel,
  onSelect,
  onDescend,
  onExit,
}: {
  doc: MapDocument;
  theme: 'dark' | 'light';
  sel: Selection;
  onSelect: (s: Selection) => void;
  onDescend: (id: string, name: string | null) => void;
  onExit: (depth: number, id: string) => void;
}) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [ghosts, setGhosts] = useState<Node[]>([]);
  const [showGhosts, setShowGhosts] = useState(false);
  const { fitView } = useReactFlow();
  const box = useRef<HTMLDivElement>(null);
  // Whether the view is the reader's doing. Until they pan or zoom, the map is
  // ours to keep framed; once they've chosen a view, resizing must not throw it
  // away. A ref, not state — the observer below shouldn't be rebuilt for it.
  const touched = useRef(false);

  // Widening the panel takes the map's space. Without this the map keeps its
  // zoom and simply gets cut off at the edge, which reads as the map being
  // clipped rather than making room. Refitting on every resize frame follows
  // the drag instead.
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      if (!touched.current) fitView({ padding: 0.15, duration: 0 });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [fitView]);

  const colorOf = useMemo(() => {
    const m = new Map(doc.subsystems.map((s, i) => [s.id, PALETTE[i % PALETTE.length]]));
    return (sid: string) => m.get(sid) ?? '#8a93ad';
  }, [doc]);

  const edges = useMemo(
    () => buildEdges(doc, sel, colorOf).concat(buildExitEdges(doc, sel)),
    [doc, sel, colorOf],
  );

  useEffect(() => {
    let alive = true;
    place(doc).then((pos) => {
      if (!alive) return;
      setNodes(buildNodes(doc, pos).concat(buildExits(doc, pos)));
      setGhosts(buildGhosts(doc, pos));
      setShowGhosts(false);
      touched.current = false; // a new altitude is a new picture to frame
      requestAnimationFrame(() => fitView({ padding: 0.15 }));
    });
    return () => {
      alive = false;
    };
  }, [doc, fitView]);

  const allNodes = useMemo(
    () => (showGhosts ? nodes.concat(ghosts) : nodes),
    [nodes, ghosts, showGhosts],
  );

  return (
    <div className="flow-fill" ref={box}>
      <ReactFlow
        nodes={allNodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        // A real gesture carries an event; our own fitView calls don't. So this
        // fires only when the reader moves the view themselves.
        onMoveStart={(e) => {
          if (e) touched.current = true;
        }}
        onNodesChange={(changes) => setNodes((ns) => applyNodeChanges(changes, ns))}
        onNodeClick={(_, n) => {
          if (n.type === 'exit') {
            // A door out: climb to where that subsystem lives and pick it.
            const { target, depth } = n.data as { target: string; depth: number };
            onExit(depth, target);
          } else if (n.type === 'ghost') {
            // An unwired file. Nothing to group, but it's still code you can read.
            onSelect({ kind: 'file', id: (n.data as { full: string }).full });
          } else if (n.type === 'subsystem') {
            onSelect({ kind: 'box', id: n.id });
          }
        }}
        // Inside. A file has no inside, so the bottom of a descent stays put.
        onNodeDoubleClick={(_, n) => {
          if (n.type !== 'subsystem' || doc.floor) return;
          onDescend(n.id, (n.data as { label: string }).label);
        }}
        onEdgeClick={(_, e) => {
          if (!e.className?.includes('is-exit')) onSelect({ kind: 'connection', id: e.id });
        }}
        onPaneClick={() => onSelect(null)}
        proOptions={{ hideAttribution: true }}
        minZoom={0.2}
        colorMode={theme}
      >
        <Background gap={24} color={theme === 'dark' ? '#1a1f2b' : '#dde2ea'} />
        {/* Fit-view is also how you hand the framing back: after this, the map
            keeps itself framed again as the panel moves. */}
        <Controls
          showInteractive={false}
          onFitView={() => {
            touched.current = false;
            fitView({ padding: 0.15, duration: 300 });
          }}
        />
        {doc.tray.n_files > 0 && (
          <Panel position="bottom-right">
            <button
              className={`chip${showGhosts ? ' chip-on' : ''}`}
              disabled={!ghosts.length}
              title={ghosts.length ? undefined : 're-map to list these files'}
              onClick={() => setShowGhosts((v) => !v)}
            >
              {doc.tray.n_files} unwired file{doc.tray.n_files === 1 ? '' : 's'}
            </button>
          </Panel>
        )}
      </ReactFlow>
    </div>
  );
}
