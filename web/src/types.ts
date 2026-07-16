// The map document, as served by the local process (see engine/map.py).

// One named thing the source file takes from the target, and how (see
// CONTEXT.md: Reference). Absent on crossings from documents cached before
// references existed; a re-map fills it in.
export interface Reference {
  name: string;
  kind: 'call' | 'import' | 'use';
  // Both ends: where the source file uses it, and where the target defines it.
  // Either can be null when graphify didn't report a position.
  line?: number | null;
  def_line?: number | null;
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
  // Set at a descent's floor, where a box is a single file rather than a
  // group of them. Its name is the filename.
  file?: string;
}

// Something the inside of a subsystem touches beyond itself: a sibling next
// door, or something further out. `out`/`in` are the ids of the boxes on this
// map that reach it / that it reaches into. `path` is where it lives — always
// back up the way you came, so the page walks to it by trimming its trail.
export interface Exit {
  id: string;
  name: string | null;
  icon: string | null;
  path: string[];
  out: string[];
  in: string[];
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
  // Present only on a descent — the top map has no parent, no floor, no exits.
  parent?: { id: string; name: string | null; description: string | null; icon: string | null };
  floor?: boolean;
  exits?: Exit[];
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
