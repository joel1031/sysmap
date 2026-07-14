import { useCallback, useState } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import { fetchMap } from './api';
import type { MapDocument } from './types';
import { MapView } from './MapView';
import type { Placement } from './layout';
import './App.css';

export default function App() {
  const [repo, setRepo] = useState('');
  const [targets, setTargets] = useState('src');
  const [doc, setDoc] = useState<MapDocument | null>(null);
  const [mode, setMode] = useState<Placement>('rows');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (refresh = false) => {
      setBusy(true);
      setError(null);
      try {
        setDoc(await fetchMap(repo.trim(), targets.split(/[\s,]+/).filter(Boolean), refresh));
      } catch (e) {
        setError(String(e));
      } finally {
        setBusy(false);
      }
    },
    [repo, targets],
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
        <input
          value={targets}
          onChange={(e) => setTargets(e.target.value)}
          placeholder="target dirs (e.g. src, or: apps packages)"
          size={24}
        />
        <button onClick={() => load()} disabled={busy || !repo.trim()}>
          {busy ? 'running the pipeline…' : 'map it'}
        </button>
        <div className="mode">
          <button className={mode === 'rows' ? 'on' : ''} onClick={() => setMode('rows')}>
            rows
          </button>
          <button className={mode === 'settle' ? 'on' : ''} onClick={() => setMode('settle')}>
            settle
          </button>
        </div>
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
            <MapView doc={doc} mode={mode} />
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
