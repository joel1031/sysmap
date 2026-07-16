import type { MapDocument } from './types';

const SERVER = 'http://localhost:8642';

export async function fetchMap(repo: string, refresh = false): Promise<MapDocument> {
  const params = new URLSearchParams({ repo });
  if (refresh) params.set('refresh', 'true');
  const res = await fetch(`${SERVER}/map?${params}`);
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}

// The inside of one subsystem, as its own map. `path` is the trail of box ids
// from the top down; the last is the one being opened. The first descent into
// a given box runs the pipeline over its files, so it can take a few seconds —
// after that the server has it.
export async function fetchDescent(repo: string, path: string[]): Promise<MapDocument> {
  const params = new URLSearchParams({ repo, path: path.join(',') });
  const res = await fetch(`${SERVER}/descend?${params}`);
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}

// One source file, whole. Cached per path for the session: reading several
// references in the same file costs one request.
const fileCache = new Map<string, Promise<string>>();

export function fetchFile(repo: string, path: string): Promise<string> {
  const key = `${repo}|${path}`;
  let hit = fileCache.get(key);
  if (!hit) {
    hit = (async () => {
      const params = new URLSearchParams({ repo, path });
      const res = await fetch(`${SERVER}/file?${params}`);
      if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
      return res.text();
    })();
    fileCache.set(key, hit);
    hit.catch(() => fileCache.delete(key)); // a failure shouldn't be remembered
  }
  return hit;
}

// The connection's one-sentence summary, delivered in text deltas as the model
// writes it. `onDelta` fires per chunk; resolves when the stream ends.
export async function streamConnectionSummary(
  repo: string,
  id: string,
  onDelta: (text: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const params = new URLSearchParams({ repo, id });
  const res = await fetch(`${SERVER}/connection?${params}`, { signal });
  if (!res.ok || !res.body) throw new Error(`${res.status}`);
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    onDelta(dec.decode(value, { stream: true }));
  }
}
