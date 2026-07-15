import { useEffect, useState } from 'react';
import type { MapDocument, Reference } from './types';
import type { Selection } from './MapView';
import { iconFor } from './SubsystemBox';
import { streamConnectionSummary } from './api';

// The app's one detail surface. A permanent right-hand panel that reflects the
// current selection: a subsystem, a connection, or (nothing) a guiding line.
// The map keeps the spatial "which"; this panel holds the "what".

const REPO = new URLSearchParams(window.location.search).get('repo') ?? '';
const VERB: Record<string, string> = { call: 'calls', import: 'imports', use: 'uses' };
const base = (p: string) => p.split('/').pop() ?? p;

// A crossing's references as one line: "calls a, b · imports c".
function refsLine(refs?: Reference[]): string {
  if (!refs || !refs.length) return '';
  const byKind: Record<string, string[]> = {};
  for (const r of refs) (byKind[r.kind] ??= []).push(r.name);
  return ['call', 'use', 'import']
    .filter((k) => byKind[k])
    .map((k) => `${VERB[k]} ${byKind[k].join(', ')}`)
    .join(' · ');
}

export function DetailPanel({
  doc,
  sel,
  onSelect,
  onClose,
}: {
  doc: MapDocument;
  sel: Selection;
  onSelect: (s: Selection) => void;
  onClose: () => void;
}) {
  return (
    <aside className="detail-panel">
      <button className="panel-close" onClick={onClose} title="close — focus the map">
        ×
      </button>
      {sel === null && (
        <div className="panel-empty">
          Select a subsystem or connection to explore how it fits.
        </div>
      )}
      {sel?.kind === 'box' && <BoxView doc={doc} id={sel.id} onSelect={onSelect} />}
      {sel?.kind === 'connection' && <ConnectionView doc={doc} id={sel.id} />}
    </aside>
  );
}

function BoxView({
  doc,
  id,
  onSelect,
}: {
  doc: MapDocument;
  id: string;
  onSelect: (s: Selection) => void;
}) {
  const s = doc.subsystems.find((x) => x.id === id);
  if (!s) return null;
  const Icon = iconFor(s.icon);
  const nameOf = (sid: string) =>
    doc.subsystems.find((x) => x.id === sid)?.name ?? 'unnamed subsystem';

  // Its role, from the backbone: what it reaches into and what reaches into it.
  const into: { name: string; connId: string }[] = [];
  const from: { name: string; connId: string }[] = [];
  for (const c of doc.connections) {
    if (!c.on_backbone || !c.subsystems.includes(id)) continue;
    for (const d of c.directions) {
      if (d.grade !== 'major') continue;
      if (d.source === id) into.push({ name: nameOf(d.target), connId: c.id });
      if (d.target === id) from.push({ name: nameOf(d.source), connId: c.id });
    }
  }

  return (
    <div className="panel-body">
      <h3 className="panel-title">
        {Icon && <Icon size={18} strokeWidth={2.1} />}
        {s.name ?? 'unnamed subsystem'}
      </h3>
      {s.description && <p className="panel-desc">{s.description}</p>}
      <div className="panel-fact">
        {s.files.length} file{s.files.length === 1 ? '' : 's'}
        {s.island ? ' · no connections — fully self-contained' : ''}
      </div>
      <Relations label="Reaches into" items={into} onSelect={onSelect} />
      <Relations label="Reached into by" items={from} onSelect={onSelect} />
    </div>
  );
}

function Relations({
  label,
  items,
  onSelect,
}: {
  label: string;
  items: { name: string; connId: string }[];
  onSelect: (s: Selection) => void;
}) {
  if (!items.length) return null;
  return (
    <div className="panel-section">
      <div className="panel-section-label">{label}</div>
      <ul className="relation-list">
        {items.map((it, i) => (
          <li key={i}>
            <button
              className="relation"
              onClick={() => onSelect({ kind: 'connection', id: it.connId })}
            >
              {it.name}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ConnectionView({ doc, id }: { doc: MapDocument; id: string }) {
  const c = doc.connections.find((x) => x.id === id);
  const [text, setText] = useState('');
  const [status, setStatus] = useState<'loading' | 'streaming' | 'done' | 'error'>('loading');

  useEffect(() => {
    if (!c) return;
    const ctrl = new AbortController();
    setText('');
    setStatus('loading');
    let got = false;
    streamConnectionSummary(
      REPO,
      id,
      (delta) => {
        got = true;
        setStatus('streaming');
        setText((t) => t + delta);
      },
      ctrl.signal,
    )
      .then(() => setStatus(got ? 'done' : 'error'))
      .catch((e) => {
        if (e.name !== 'AbortError') setStatus('error');
      });
    return () => ctrl.abort();
  }, [id, c]);

  if (!c) return null;
  const nameOf = (sid: string) =>
    doc.subsystems.find((x) => x.id === sid)?.name ?? 'unnamed subsystem';
  const mutual = c.directions.length > 1;
  const head = mutual
    ? `${nameOf(c.subsystems[0])}  ⇄  ${nameOf(c.subsystems[1])}`
    : `${nameOf(c.directions[0].source)}  →  ${nameOf(c.directions[0].target)}`;

  return (
    <div className="panel-body">
      <h3 className="panel-title panel-conn-head">{head}</h3>
      <div className="panel-sentence">
        {status === 'error' ? (
          <span className="panel-fail">Couldn't generate a summary.</span>
        ) : text ? (
          <>
            {text}
            {status === 'streaming' && <span className="cursor" />}
          </>
        ) : (
          <span className="panel-dim">Summarizing…</span>
        )}
      </div>
      {c.directions.map((d, i) => (
        <div className="panel-section" key={i}>
          {mutual && (
            <div className="panel-section-label">
              {nameOf(d.source)} → {nameOf(d.target)}
            </div>
          )}
          <ul className="crossing-list">
            {d.crossings.map((x, j) => (
              <li key={j} className="crossing-row">
                <span className="files">
                  <span title={x.from}>{base(x.from)}</span> →{' '}
                  <span title={x.to}>{base(x.to)}</span>
                </span>
                {refsLine(x.references) && <span className="refs">{refsLine(x.references)}</span>}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
