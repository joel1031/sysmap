import type { MapDocument } from './types';

const SERVER = 'http://localhost:8642';

export async function fetchMap(repo: string, refresh = false): Promise<MapDocument> {
  const params = new URLSearchParams({ repo });
  if (refresh) params.set('refresh', 'true');
  const res = await fetch(`${SERVER}/map?${params}`);
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}
