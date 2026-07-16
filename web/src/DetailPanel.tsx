import { useEffect, useState } from 'react';
import type { Exit, MapDocument, Reference } from './types';
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
  onDescend,
  onBack,
  canBack,
  onClose,
}: {
  doc: MapDocument;
  sel: Selection;
  onSelect: (s: Selection) => void;
  onDescend: (id: string, name: string | null) => void;
  onBack: () => void;
  canBack: boolean;
  onClose: () => void;
}) {
  return (
    <aside className="detail-panel">
      <div className="panel-nav">
        {canBack ? (
          <button className="panel-back" onClick={onBack} title="back to the last thing">
            ‹ Back
          </button>
        ) : (
          <span />
        )}
        <button className="panel-close" onClick={onClose} title="close — focus the map">
          ×
        </button>
      </div>
      {/* Nothing picked. Inside a subsystem that's still a question with an
          answer — the subsystem you're standing in. At the top it isn't. */}
      {sel === null &&
        (doc.parent ? (
          <ParentView doc={doc} />
        ) : (
          <div className="panel-empty">
            Select a subsystem or connection to explore its relationships.
          </div>
        ))}
      {sel?.kind === 'box' && (
        <BoxView doc={doc} id={sel.id} onSelect={onSelect} onDescend={onDescend} />
      )}
      {sel?.kind === 'connection' && <ConnectionView doc={doc} id={sel.id} />}
    </aside>
  );
}

// Where you are, when you're inside something and haven't picked anything in
// it. Its exits are the same wiring the ghost markers draw on the canvas.
function ParentView({ doc }: { doc: MapDocument }) {
  const p = doc.parent;
  if (!p) return null;
  const Icon = iconFor(p.icon);
  const n = doc.subsystems.reduce((a, s) => a + s.files.length, 0);
  return (
    <div className="panel-body">
      <h3 className="panel-title">
        {Icon && <Icon size={18} strokeWidth={2.1} />}
        {p.name ?? 'unnamed subsystem'}
      </h3>
      {p.description && <p className="panel-desc">{p.description}</p>}
      <div className="panel-fact">
        You're inside — {n} file{n === 1 ? '' : 's'}
        {doc.floor
          ? ', shown as themselves'
          : `, in ${doc.subsystems.length} piece${doc.subsystems.length === 1 ? '' : 's'}`}
      </div>
      <ExitList label="Reaches into" items={(doc.exits ?? []).filter((e) => e.out.length)} />
      <ExitList label="Reached into by" items={(doc.exits ?? []).filter((e) => e.in.length)} />
    </div>
  );
}

function ExitList({ label, items }: { label: string; items: Exit[] }) {
  if (!items.length) return null;
  return (
    <div className="panel-section">
      <div className="panel-section-label">{label}</div>
      <ul className="relation-list">
        {items.map((e) => (
          <li key={e.id}>
            <span className="relation is-outside" title="outside this subsystem">
              {e.name ?? 'elsewhere'}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function BoxView({
  doc,
  id,
  onSelect,
  onDescend,
}: {
  doc: MapDocument;
  id: string;
  onSelect: (s: Selection) => void;
  onDescend: (id: string, name: string | null) => void;
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
      {/* A file has no inside. Anything else does. */}
      {!s.file && (
        <button className="explore" onClick={() => onDescend(s.id, s.name)}>
          Explore inside ↓
        </button>
      )}
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
