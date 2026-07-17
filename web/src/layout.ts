// Placement: boxes stacked so the major arrows all point downward — a box
// sits above the boxes it depends on. Same document, same picture, every time.
// Chosen by looking at a small app and hono side by side against the
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

// An exit is laid out with everything else rather than pinned to a corner, so
// it lands on the side its wiring actually comes from: something the inside
// reaches settles below it, something reaching in settles above.
export const exitId = (id: string) => `exit-${id}`;
const exitW = (name: string | null) => 30 + (name ?? 'elsewhere').length * 6.6;
const EXIT_H = 30;

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
      // Wide lanes inside a row so lines can pass between boxes, tighter
      // rows so long lines travel less, and box placement that favors
      // straight lines over a centered column (the centered default funnels
      // every long connection through the same middle corridor).
      'elk.spacing.nodeNode': '110',
      'elk.layered.spacing.nodeNodeBetweenLayers': '80',
      'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
      'elk.layered.thoroughness': '30',
    },
    children: [
      ...doc.subsystems.map((s) => ({
        id: s.id,
        width: dims(s).w,
        height: dims(s).h,
      })),
      ...(doc.exits ?? []).map((e) => ({
        id: exitId(e.id),
        width: exitW(e.name),
        height: EXIT_H,
      })),
    ],
    edges: [
      ...majors.map((d, i) => ({
        id: `e${i}`,
        sources: [d.source],
        targets: [d.target],
      })),
      ...(doc.exits ?? []).flatMap((e) => [
        ...e.out.map((b) => ({ id: `xo${e.id}${b}`, sources: [b], targets: [exitId(e.id)] })),
        ...e.in.map((b) => ({ id: `xi${e.id}${b}`, sources: [exitId(e.id)], targets: [b] })),
      ]),
    ],
  };
  const out = await elk.layout(graph);
  const pos: Positions = {};
  for (const n of out.children ?? []) pos[n.id] = { x: n.x ?? 0, y: n.y ?? 0 };
  return pos;
}
