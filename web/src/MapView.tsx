import { useEffect, useMemo, useState } from 'react';
import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  useReactFlow,
} from '@xyflow/react';
import type { Edge, Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { MapDocument } from './types';
import { place } from './layout';
import type { Positions } from './layout';
import { SubsystemBox } from './SubsystemBox';

// Vivid enough to read as outlines on near-black, mid enough for light mode.
const PALETTE = [
  '#5c7cfa', '#22c1a3', '#e8a33d', '#e05f8a', '#9a6dd7', '#38b6d9',
  '#a3b845', '#e07a4f', '#5fa87a', '#c46a9e', '#8a93ad', '#d9b96a',
  '#5f9ea0',
];

const nodeTypes = { subsystem: SubsystemBox };

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

// One line per pair: the connection. Thickness is the pair's crossings;
// an arrowhead on each end that has a major dependency pointing at it.
function buildEdges(doc: MapDocument): Edge[] {
  const drawn = doc.connections.filter((c) => c.on_backbone);
  const maxW = Math.max(
    1,
    ...drawn.map((c) => c.directions.reduce((a, d) => a + d.weight, 0)),
  );
  return drawn.map((c) => {
    const majors = c.directions.filter((d) => d.grade === 'major');
    const weight = c.directions.reduce((a, d) => a + d.weight, 0);
    const [source, target] = [majors[0].source, majors[0].target];
    const twoHeaded = majors.length === 2;
    const width = 1.5 + 4.5 * (weight / maxW);
    return {
      id: c.id,
      source,
      target,
      style: { strokeWidth: width },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#7a8499', width: 18 / width + 8, height: 18 / width + 8 },
      markerStart: twoHeaded
        ? { type: MarkerType.ArrowClosed, color: '#7a8499', width: 18 / width + 8, height: 18 / width + 8 }
        : undefined,
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
