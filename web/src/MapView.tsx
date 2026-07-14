import { useEffect, useMemo, useState } from 'react';
import {
  Background,
  Controls,
  ReactFlow,
  useReactFlow,
} from '@xyflow/react';
import type { Edge, Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { MapDocument } from './types';
import { place } from './layout';
import type { Positions } from './layout';
import { SubsystemBox } from './SubsystemBox';
import { ConnectionEdge } from './ConnectionEdge';

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
function buildEdges(doc: MapDocument): Edge[] {
  return doc.connections
    .filter((c) => c.on_backbone)
    .map((c) => {
      const drawn = c.directions.find((d) => d.grade === 'major') ?? c.directions[0];
      return {
        id: c.id,
        source: drawn.source,
        target: drawn.target,
        type: 'connection',
      };
    });
}

export function MapView({ doc, theme }: { doc: MapDocument; theme: 'dark' | 'light' }) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const edges = useMemo(() => buildEdges(doc), [doc]);
  const { fitView } = useReactFlow();

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
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      onNodesChange={() => {}}
      proOptions={{ hideAttribution: true }}
      minZoom={0.2}
      colorMode={theme}
    >
      <Background gap={24} color={theme === 'dark' ? '#1a1f2b' : '#dde2ea'} />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}
