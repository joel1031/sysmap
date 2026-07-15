import { useReactFlow, useViewport } from '@xyflow/react';
import type { Node } from '@xyflow/react';
import type { MapDocument } from './types';
import type { Selection } from './MapView';

// The anchored card for a connection: appears beside the line you clicked, so
// the words land where you're already looking. This is where a line's weight
// lives — the direction(s) and every crossing behind it. Boxes have no card;
// what a box has to say fits in the corner strip.
export function DetailCard({
  doc,
  sel,
  nodes,
}: {
  doc: MapDocument;
  sel: Extract<NonNullable<Selection>, { kind: 'connection' }>;
  nodes: Node[];
}) {
  const { flowToScreenPosition } = useReactFlow();
  useViewport(); // re-anchor while panning/zooming

  const byId = new Map(nodes.map((n) => [n.id, n]));
  const c = doc.connections.find((x) => x.id === sel.id);
  if (!c) return null;
  const [a, b] = c.subsystems.map((id) => byId.get(id));
  if (!a || !b) return null;

  const anchor = flowToScreenPosition({
    x: (a.position.x + b.position.x) / 2 + 100,
    y: (a.position.y + b.position.y) / 2,
  });
  const nameOf = (sid: string) =>
    doc.subsystems.find((s) => s.id === sid)?.name ?? 'unnamed subsystem';

  const left = Math.min(anchor.x, window.innerWidth - 380);
  const top = Math.min(Math.max(anchor.y, 60), window.innerHeight - 200);
  return (
    <div className="detail-card" style={{ left, top }}>
      {c.directions.map((d, i) => (
        <div key={i} className="direction">
          <h4>
            {nameOf(d.source)} → {nameOf(d.target)}
          </h4>
          <div className="fact">
            {d.weight} crossing{d.weight === 1 ? '' : 's'}
            {d.grade === 'minor' ? ' · minor' : ''}
          </div>
          <div className="crossings">
            {d.crossings.map((x, j) => (
              <div key={j}>
                {x.from} → {x.to}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
