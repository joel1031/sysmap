// The two placement modes. Both take the map document and return a position
// for every drawn box; which one runs is a switch in the UI (Phase 4 picks the
// winner by looking).
import ELK from 'elkjs/lib/elk.bundled.js';
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
} from 'd3-force';
import type { SimulationNodeDatum } from 'd3-force';
import type { MapDocument, Subsystem } from './types';

export type Placement = 'rows' | 'settle';

// Box dimensions per size step. Size means how much code (three steps, floored).
export const BOX_SIZE: Record<number, { w: number; h: number }> = {
  1: { w: 140, h: 52 },
  2: { w: 180, h: 64 },
  3: { w: 230, h: 80 },
};

export interface Positions {
  [id: string]: { x: number; y: number };
}

function dims(s: Subsystem) {
  return BOX_SIZE[s.size_step];
}

// Rows: boxes stacked so the major arrows all point downward — a box sits
// above the boxes it depends on. Same document, same picture, every time.
export async function rowsPlacement(doc: MapDocument): Promise<Positions> {
  const elk = new ELK();
  const majors = doc.connections.flatMap((c) =>
    c.directions.filter((d) => d.grade === 'major'),
  );
  const graph = {
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': 'DOWN',
      'elk.spacing.nodeNode': '60',
      'elk.layered.spacing.nodeNodeBetweenLayers': '90',
    },
    children: doc.subsystems.map((s) => ({
      id: s.id,
      width: dims(s).w,
      height: dims(s).h,
    })),
    edges: majors.map((d, i) => ({
      id: `e${i}`,
      sources: [d.source],
      targets: [d.target],
    })),
  };
  const out = await elk.layout(graph);
  const pos: Positions = {};
  for (const n of out.children ?? []) pos[n.id] = { x: n.x ?? 0, y: n.y ?? 0 };
  return pos;
}

interface SettleNode extends SimulationNodeDatum {
  id: string;
  w: number;
  h: number;
}

// Settle: connections act as rubber bands, boxes repel each other, and the
// picture is wherever that comes to rest. Position carries no meaning.
export async function settlePlacement(doc: MapDocument): Promise<Positions> {
  const nodes: SettleNode[] = doc.subsystems.map((s) => ({ id: s.id, ...dims(s) }));
  const links = doc.connections
    .filter((c) => c.on_backbone)
    .map((c) => ({ source: c.subsystems[0], target: c.subsystems[1] }));
  forceSimulation(nodes)
    .force('link', forceLink<SettleNode, (typeof links)[number]>(links).id((n) => n.id).distance(200))
    .force('charge', forceManyBody().strength(-1200))
    .force('center', forceCenter(0, 0))
    .force('collide', forceCollide<SettleNode>().radius((n) => Math.hypot(n.w, n.h) / 2 + 20))
    .stop()
    .tick(300);
  const pos: Positions = {};
  for (const n of nodes) pos[n.id] = { x: n.x ?? 0, y: n.y ?? 0 };
  return pos;
}

export function place(doc: MapDocument, mode: Placement): Promise<Positions> {
  return mode === 'rows' ? rowsPlacement(doc) : settlePlacement(doc);
}
