import type { NodeProps } from '@xyflow/react';

// A noise file made visible: a faint dashed outline with the file's name,
// laid along the map's bottom edge. Toggled by the corner chip; not
// draggable, not selectable — present, but visibly lighter-weight than a
// subsystem box.
export function GhostBox({ data }: NodeProps) {
  const { label, full } = data as { label: string; full: string };
  return (
    <div className="ghost-box" title={full}>
      {label}
    </div>
  );
}
