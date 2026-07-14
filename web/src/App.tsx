import { useCallback, useEffect, useState } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import { fetchMap } from './api';
import type { MapDocument } from './types';
import { MapView } from './MapView';
import './App.css';

// The `map` command resolves the repo (walking up to .git from wherever you
// ran it) and opens this page with ?repo=<path> - there is nothing to type
// here. Opening the page without that param means it wasn't launched via the
// command.
const REPO = new URLSearchParams(window.location.search).get('repo');

export default function App() {
  const [doc, setDoc] = useState<MapDocument | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

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
              {doc.tray.count > 0 && <> · tray: {doc.tray.count}</>}
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
          <ReactFlowProvider>
            <MapView doc={doc} theme={theme} />
          </ReactFlowProvider>
        )}
      </main>
    </div>
  );
}
