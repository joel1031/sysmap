import { useCallback, useEffect, useState } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import { fetchMap } from './api';
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

// Two selections are the same pick if they point at the same thing.
function sameSel(a: Selection, b: Selection): boolean {
  return a === b || (!!a && !!b && a.kind === b.kind && a.id === b.id);
}

export default function App() {
  const [doc, setDoc] = useState<MapDocument | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [sel, setSel] = useState<Selection>(null);
  const [history, setHistory] = useState<Selection[]>([]);
  const [panelOpen, setPanelOpen] = useState(true);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  // Selecting anything opens the panel and remembers where you were, so Back
  // can return to it. Re-picking the same thing doesn't add a step, and the
  // empty start isn't worth going back to.
  const select = useCallback(
    (s: Selection) => {
      if (sameSel(sel, s)) {
        if (s) setPanelOpen(true);
        return;
      }
      if (sel) setHistory((h) => [...h, sel]);
      setSel(s);
      if (s) setPanelOpen(true);
    },
    [sel],
  );

  const back = useCallback(() => {
    if (!history.length) return;
    const prev = history[history.length - 1];
    setHistory((h) => h.slice(0, -1));
    setSel(prev);
    if (prev) setPanelOpen(true);
  }, [history]);

  // A fresh map clears the selection and its history.
  useEffect(() => {
    setSel(null);
    setHistory([]);
  }, [doc]);

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
      setDoc(await fetchMap(REPO, refresh));
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
        <strong>{doc ? doc.repo : 'codebase map'}</strong>
        {doc && (
          <>
            <span className="meta">
              {doc.subsystems.length} subsystems · {backboneCount} connections
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
        {busy && !doc && <div className="empty">Running the pipeline…</div>}
        {doc && (
          <div className="workspace">
            <div className="map-area">
              <ReactFlowProvider>
                <MapView doc={doc} theme={theme} sel={sel} onSelect={select} />
              </ReactFlowProvider>
            </div>
            {panelOpen ? (
              <DetailPanel
                doc={doc}
                sel={sel}
                onSelect={select}
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
