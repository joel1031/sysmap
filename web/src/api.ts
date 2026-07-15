import type { MapDocument } from './types';

const SERVER = 'http://localhost:8642';

export async function fetchMap(repo: string, refresh = false): Promise<MapDocument> {
  const params = new URLSearchParams({ repo });
  if (refresh) params.set('refresh', 'true');
  const res = await fetch(`${SERVER}/map?${params}`);
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
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
