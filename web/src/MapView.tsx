import { useEffect, useMemo, useState } from 'react';
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
import { place } from './layout';
import type { Positions } from './layout';
import { SubsystemBox } from './SubsystemBox';
import { GhostBox } from './GhostBox';
import { ConnectionEdge } from './ConnectionEdge';
import type { Flow } from './ConnectionEdge';
import { DetailCard } from './DetailCard';

// What's picked right now: a box, a connection, or nothing. Picking a box
// animates every connection touching it, in each dependency's true
// direction; picking a connection animates just that one.
export type Selection =
  | { kind: 'box'; id: string }
  | { kind: 'connection'; id: string }
  | null;

// Vivid enough to read as outlines on near-black, mid enough for light mode.
const PALETTE = [
  '#5c7cfa', '#22c1a3', '#e8a33d', '#e05f8a', '#9a6dd7', '#38b6d9',
  '#a3b845', '#e07a4f', '#5fa87a', '#c46a9e', '#8a93ad', '#d9b96a',
  '#5f9ea0',
];

const nodeTypes = { subsystem: SubsystemBox, ghost: GhostBox };
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
    },
  }));
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
      return {
        id: c.id,
        source: drawn.source,
        target: drawn.target,
        type: 'connection',
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
      selectable: false,
      data: { label, full: f },
    };
    x += w + 10;
    return node;
  });
}

export function MapView({ doc, theme }: { doc: MapDocument; theme: 'dark' | 'light' }) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [ghosts, setGhosts] = useState<Node[]>([]);
  const [showGhosts, setShowGhosts] = useState(false);
  const [sel, setSel] = useState<Selection>(null);
  const { fitView } = useReactFlow();

  const colorOf = useMemo(() => {
    const m = new Map(doc.subsystems.map((s, i) => [s.id, PALETTE[i % PALETTE.length]]));
    return (sid: string) => m.get(sid) ?? '#8a93ad';
  }, [doc]);

  const edges = useMemo(() => buildEdges(doc, sel, colorOf), [doc, sel, colorOf]);

  useEffect(() => {
    setSel(null);
  }, [doc]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSel(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => {
    let alive = true;
    place(doc).then((pos) => {
      if (!alive) return;
      setNodes(buildNodes(doc, pos));
      setGhosts(buildGhosts(doc, pos));
      setShowGhosts(false);
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
    <>
      <ReactFlow
        nodes={allNodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={(changes) => setNodes((ns) => applyNodeChanges(changes, ns))}
        onNodeClick={(_, n) => setSel({ kind: 'box', id: n.id })}
        onEdgeClick={(_, e) => setSel({ kind: 'connection', id: e.id })}
        onPaneClick={() => setSel(null)}
        proOptions={{ hideAttribution: true }}
        minZoom={0.2}
        colorMode={theme}
      >
        <Background gap={24} color={theme === 'dark' ? '#1a1f2b' : '#dde2ea'} />
        <Controls showInteractive={false} />
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
      {sel && <DetailCard doc={doc} sel={sel} nodes={nodes} />}
    </>
  );
}
