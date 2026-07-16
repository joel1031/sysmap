import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import { fetchDescent, fetchMap } from './api';
import type { MapDocument } from './types';
import { MapView } from './MapView';
import type { Selection } from './MapView';
import { DetailPanel } from './DetailPanel';
import './App.css';

// The `map` command resolves the repo (walking up to .git from wherever you
// ran it) and opens this page with ?repo=<path> - there is nothing to type
// here. Opening the page without that param means it wasn't launched via the
// command.
const REPO = new URLSearchParams(window.location.search).get('repo');

// One box you went inside of. The name rides along so the trail can be drawn
// without holding on to every map you passed through.
export interface Step {
  id: string;
  name: string;
}

// Where you are: how far down, and what's picked there. Both move, so both are
// remembered together — see `go`.
interface Where {
  path: Step[];
  sel: Selection;
}

// Two selections are the same pick if they point at the same thing.
function sameSel(a: Selection, b: Selection): boolean {
  return a === b || (!!a && !!b && a.kind === b.kind && a.id === b.id);
}

function samePath(a: Step[], b: Step[]): boolean {
  return a.length === b.length && a.every((s, i) => s.id === b[i].id);
}

// Work happening where the map should be. It covers the map rather than
// sitting in a corner: until an altitude is computed, the boxes underneath are
// the ones you were looking at *before*, and leaving them on display asserts a
// place you aren't yet.
function Loading({ title, note }: { title: string; note: string }) {
  return (
    <div className="loading" role="status" aria-live="polite">
      <div className="loading-card">
        <div className="spinner" />
        <div className="loading-title">{title}</div>
        <div className="loading-note">{note}</div>
      </div>
    </div>
  );
}

export default function App() {
  const [top, setTop] = useState<MapDocument | null>(null);
  const [doc, setDoc] = useState<MapDocument | null>(null);
  const [path, setPath] = useState<Step[]>([]);
  const [sel, setSel] = useState<Selection>(null);
  const [history, setHistory] = useState<Where[]>([]);
  const [busy, setBusy] = useState(false);
  const [descending, setDescending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [panelOpen, setPanelOpen] = useState(true);
  // Every altitude visited this session. Climbing back is instant; the server
  // caches too, so even after a reload a re-descent costs nothing.
  const seen = useRef(new Map<string, MapDocument>());

  const pathKey = useMemo(() => path.map((s) => s.id).join(','), [path]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  // One move, whatever kind. Descending, climbing, picking and clearing all
  // come through here, so Back can undo any of them without knowing which it
  // was. The pristine start — top of the map, nothing picked — isn't worth
  // returning to, so it isn't remembered.
  const go = useCallback(
    (next: Where) => {
      const now: Where = { path, sel };
      if (samePath(now.path, next.path) && sameSel(now.sel, next.sel)) {
        if (next.sel) setPanelOpen(true);
        return;
      }
      if (now.sel || now.path.length) setHistory((h) => [...h, now]);
      setPath(next.path);
      setSel(next.sel);
      if (next.sel) setPanelOpen(true);
    },
    [path, sel],
  );

  const select = useCallback((s: Selection) => go({ path, sel: s }), [go, path]);

  // Into a box: one step further down, nothing picked inside it yet — so the
  // panel falls back to describing the box you just entered.
  const descend = useCallback(
    (id: string, name: string | null) =>
      go({ path: [...path, { id, name: name ?? 'unnamed' }], sel: null }),
    [go, path],
  );

  // The trail, clicked: climb to that altitude. Index -1 is the repo itself.
  const climb = useCallback(
    (i: number) => go({ path: path.slice(0, i + 1), sel: null }),
    [go, path],
  );

  const back = useCallback(() => {
    if (!history.length) return;
    const prev = history[history.length - 1];
    setHistory((h) => h.slice(0, -1));
    setPath(prev.path);
    setSel(prev.sel);
    if (prev.sel) setPanelOpen(true);
  }, [history]);

  // The map for wherever we're standing. The top is already in hand; anything
  // below it is fetched once and kept.
  useEffect(() => {
    if (!top || !REPO) return;
    if (!pathKey) {
      setDoc(top);
      return;
    }
    const hit = seen.current.get(pathKey);
    if (hit) {
      setDoc(hit);
      return;
    }
    let alive = true;
    setDescending(true);
    fetchDescent(REPO, pathKey.split(','))
      .then((d) => {
        if (!alive) return;
        seen.current.set(pathKey, d);
        setDoc(d);
      })
      .catch((e) => {
        if (alive) setError(String(e));
      })
      .finally(() => {
        if (alive) setDescending(false);
      });
    return () => {
      alive = false;
    };
  }, [top, pathKey]);

  // A fresh map is a fresh world: every altitude under it is stale.
  useEffect(() => {
    seen.current.clear();
    setPath([]);
    setSel(null);
    setHistory([]);
  }, [top]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') select(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [select]);

  const load = useCallback(async (refresh = false) => {
    if (!REPO) return;
    setBusy(true);
    setError(null);
    try {
      setTop(await fetchMap(REPO, refresh));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const backboneCount = doc?.connections.filter((c) => c.on_backbone).length ?? 0;

  return (
    <div className="app">
      <header>
        <strong>{top ? top.repo : 'codebase map'}</strong>
        {doc && (
          <>
            <span className="meta">
              {doc.floor ? `${doc.subsystems.length} files` : `${doc.subsystems.length} subsystems`}
              {' · '}
              {backboneCount} connections
            </span>
            <button onClick={() => load(true)} disabled={busy}>
              {busy ? 're-mapping…' : 're-map'}
            </button>
          </>
        )}
        <button
          className="theme-toggle"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          title="switch theme"
        >
          {theme === 'dark' ? '☀' : '☾'}
        </button>
      </header>
      <main>
        {!REPO && (
          <div className="error">
            No repository given. Run <code>map</code> from inside the repo you
            want to see.
          </div>
        )}
        {error && <div className="error">{error}</div>}
        {busy && !doc && (
          <Loading
            title={`Mapping ${REPO?.split('/').pop() ?? 'this repo'}`}
            note="Reading every file, working out what groups with what, and naming the pieces. The first run on a repo takes a few minutes; after that it's instant until the code changes."
          />
        )}
        {doc && (
          <div className="workspace">
            <div className="map-area">
              <ReactFlowProvider>
                <MapView
                  doc={doc}
                  theme={theme}
                  sel={sel}
                  onSelect={select}
                  onDescend={descend}
                  onExit={(depth, id) =>
                    go({ path: path.slice(0, depth), sel: { kind: 'box', id } })
                  }
                />
              </ReactFlowProvider>
              {path.length > 0 && (
                <nav className="trail" aria-label="altitude">
                  <button onClick={() => climb(-1)}>{top?.repo}</button>
                  {path.map((s, i) => (
                    <span key={s.id}>
                      <span className="trail-sep">›</span>
                      {i === path.length - 1 ? (
                        <span className="trail-here">{s.name}</span>
                      ) : (
                        <button onClick={() => climb(i)}>{s.name}</button>
                      )}
                    </span>
                  ))}
                </nav>
              )}
              {busy ? (
                <Loading
                  title={`Re-mapping ${top?.repo ?? ''}`}
                  note="The code changed, so everything is being worked out again from scratch."
                />
              ) : (
                descending && (
                  <Loading
                    title={`Looking inside ${path[path.length - 1]?.name ?? ''}`}
                    note="Re-grouping this subsystem's files into the pieces it's made of, and naming them. This happens once per subsystem — after that, going back in is instant."
                  />
                )
              )}
            </div>
            {panelOpen ? (
              <DetailPanel
                doc={doc}
                sel={sel}
                onSelect={select}
                onDescend={descend}
                onBack={back}
                canBack={history.length > 0}
                onClose={() => setPanelOpen(false)}
              />
            ) : (
              <button
                className="panel-reopen"
                onClick={() => setPanelOpen(true)}
                title="open the detail panel"
              >
                ‹
              </button>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
