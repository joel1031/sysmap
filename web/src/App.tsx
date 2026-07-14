import { useCallback, useState } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import { fetchMap } from './api';
import type { MapDocument } from './types';
import { MapView } from './MapView';
import './App.css';

export default function App() {
  const [repo, setRepo] = useState('');
  const [doc, setDoc] = useState<MapDocument | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (refresh = false) => {
      setBusy(true);
      setError(null);
      try {
        setDoc(await fetchMap(repo.trim(), refresh));
      } catch (e) {
        setError(String(e));
      } finally {
        setBusy(false);
      }
    },
    [repo],
  );

  const backboneCount = doc?.connections.filter((c) => c.on_backbone).length ?? 0;

  return (
    <div className="app">
      <header>
        <strong>{doc ? doc.repo : 'codebase map'}</strong>
        <input
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
          placeholder="/path/to/repo"
          size={38}
        />
        <button onClick={() => load()} disabled={busy || !repo.trim()}>
          {busy ? 'running the pipeline…' : 'map it'}
        </button>
        {doc && (
          <span className="meta">
            {doc.subsystems.length} subsystems · {backboneCount} connections
            {doc.tray.count > 0 && <> · tray: {doc.tray.count}</>}
          </span>
        )}
      </header>
      <main>
        {error && <div className="error">{error}</div>}
        {doc ? (
          <ReactFlowProvider>
            <MapView doc={doc} />
          </ReactFlowProvider>
        ) : (
          !error && (
            <div className="empty">
              Point it at a repository. The first look at a large codebase takes
              minutes; after that it is instant until the repo changes.
            </div>
          )
        )}
      </main>
    </div>
  );
}
