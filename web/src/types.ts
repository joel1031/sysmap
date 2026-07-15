// The map document, as served by the local process (see engine/map.py).

// One named thing the source file takes from the target, and how (see
// CONTEXT.md: Reference). Absent on crossings from documents cached before
// references existed; a re-map fills it in.
export interface Reference {
  name: string;
  kind: 'call' | 'import' | 'use';
}

export interface Crossing {
  from: string;
  to: string;
  references?: Reference[];
}

export interface Direction {
  source: string; // subsystem id
  target: string;
  weight: number; // number of crossings
  grade: 'major' | 'minor';
  crossings: Crossing[];
}

export interface Subsystem {
  id: string;
  name: string | null;
  description: string | null;
  icon: string | null;
  files: string[];
  size_step: 1 | 2 | 3;
  self_containment: number;
  minor_count: number;
  island: boolean;
}

export interface Connection {
  id: string;
  subsystems: [string, string];
  on_backbone: boolean;
  directions: Direction[];
}

export interface MapDocument {
  repo: string;
  subsystems: Subsystem[];
  connections: Connection[];
  // `files` is absent in map documents cached before it existed; a re-map
  // fills it in.
  tray: { count: number; n_files: number; files?: string[]; group_ids: string[] };
  backbone: {
    majors: number;
    dependencies: number;
    crossings_kept: number;
    n_crossings: number;
    circular_before: number;
    circular_after: number;
  };
}
