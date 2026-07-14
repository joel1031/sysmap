// Placement: boxes stacked so the major arrows all point downward — a box
// sits above the boxes it depends on. Same document, same picture, every time.
// Chosen by looking at SpendWell and hono side by side against the
// alternative (boxes repelling, connections pulling like rubber bands, no
// fixed meaning to position) — rows read as the clearer picture.
import ELK from 'elkjs/lib/elk.bundled.js';
import type { MapDocument, Subsystem } from './types';

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

export async function place(doc: MapDocument): Promise<Positions> {
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
