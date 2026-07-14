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
import type { Placement, Positions } from './layout';
import { SubsystemBox } from './SubsystemBox';

const PALETTE = [
  '#4f6df5', '#e8833a', '#3aa675', '#c0497f', '#7d5bd0', '#2f9bbf',
  '#b0913a', '#d0574f', '#5b8c3a', '#8a6d5b', '#7a7f8c', '#5f9ea0',
  '#c46a9e',
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
      style: { strokeWidth: width, stroke: '#94a0b4' },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#94a0b4', width: 18 / width + 8, height: 18 / width + 8 },
      markerStart: twoHeaded
        ? { type: MarkerType.ArrowClosed, color: '#94a0b4', width: 18 / width + 8, height: 18 / width + 8 }
        : undefined,
    };
  });
}

export function MapView({ doc, mode }: { doc: MapDocument; mode: Placement }) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const edges = useMemo(() => buildEdges(doc), [doc]);
  const { fitView } = useReactFlow();

  useEffect(() => {
    let alive = true;
    place(doc, mode).then((pos) => {
      if (!alive) return;
      setNodes(buildNodes(doc, pos));
      requestAnimationFrame(() => fitView({ padding: 0.15 }));
    });
    return () => {
      alive = false;
    };
  }, [doc, mode, fitView]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodesChange={() => {}}
      proOptions={{ hideAttribution: true }}
      minZoom={0.2}
    >
      <Background gap={24} color="#e3e7ee" />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}
