import { useReactFlow, useViewport } from '@xyflow/react';
import type { Node } from '@xyflow/react';
import type { MapDocument } from './types';
import type { Selection } from './MapView';

// The anchored card: appears beside the thing you clicked, so the words land
// where you're already looking. A box card carries only the subsystem's
// one-sentence description and its file count; a connection card is where
// weight lives — the direction(s) and every crossing behind the line.
export function DetailCard({
  doc,
  sel,
  nodes,
}: {
  doc: MapDocument;
  sel: NonNullable<Selection>;
  nodes: Node[];
}) {
  const { flowToScreenPosition } = useReactFlow();
  useViewport(); // re-anchor while panning/zooming

  const byId = new Map(nodes.map((n) => [n.id, n]));

  let anchor: { x: number; y: number };
  let body: React.ReactNode;

  if (sel.kind === 'box') {
    const s = doc.subsystems.find((x) => x.id === sel.id);
    const n = byId.get(sel.id);
    if (!s || !n) return null;
    anchor = flowToScreenPosition({
      x: n.position.x + (n.measured?.width ?? 180) + 14,
      y: n.position.y,
    });
    body = (
      <>
        <h4>{s.name ?? 'unnamed subsystem'}</h4>
        {s.description && <p>{s.description}</p>}
        <div className="fact">{s.files.length} files</div>
        {s.island && <div className="fact">no connections — fully self-contained</div>}
      </>
    );
  } else {
    const c = doc.connections.find((x) => x.id === sel.id);
    if (!c) return null;
    const [a, b] = c.subsystems.map((id) => byId.get(id));
    if (!a || !b) return null;
    anchor = flowToScreenPosition({
      x: (a.position.x + b.position.x) / 2 + 100,
      y: (a.position.y + b.position.y) / 2,
    });
    const nameOf = (sid: string) =>
      doc.subsystems.find((s) => s.id === sid)?.name ?? 'unnamed subsystem';
    body = c.directions.map((d, i) => (
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
    ));
  }

  const left = Math.min(anchor.x, window.innerWidth - 380);
  const top = Math.min(Math.max(anchor.y, 60), window.innerHeight - 200);
  return (
    <div className="detail-card" style={{ left, top }}>
      {body}
    </div>
  );
}
