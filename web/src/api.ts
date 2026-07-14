import type { MapDocument } from './types';

const SERVER = 'http://localhost:8642';

export async function fetchMap(
  repo: string,
  targets: string[],
  refresh = false,
): Promise<MapDocument> {
  const params = new URLSearchParams();
  params.set('repo', repo);
  for (const t of targets) params.append('target', t);
  if (refresh) params.set('refresh', 'true');
  const res = await fetch(`${SERVER}/map?${params}`);
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}
