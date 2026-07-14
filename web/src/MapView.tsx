import { useEffect, useMemo, useState } from 'react';
import {
  Background,
  Controls,
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

const nodeTypes = { subsystem: SubsystemBox };
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
      const flows: Flow[] = active
        ? c.directions.map((d) => ({
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

export function MapView({ doc, theme }: { doc: MapDocument; theme: 'dark' | 'light' }) {
  const [nodes, setNodes] = useState<Node[]>([]);
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
      requestAnimationFrame(() => fitView({ padding: 0.15 }));
    });
    return () => {
      alive = false;
    };
  }, [doc, fitView]);

  return (
    <>
      <ReactFlow
        nodes={nodes}
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
      </ReactFlow>
      {sel && <DetailCard doc={doc} sel={sel} nodes={nodes} />}
    </>
  );
}
