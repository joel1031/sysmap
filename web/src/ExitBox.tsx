import type { NodeProps } from '@xyflow/react';
import { Handle, Position } from '@xyflow/react';
import { iconFor } from './SubsystemBox';

// Somewhere beyond the subsystem you're inside of, drawn at the edge of its
// map: a sibling next door, or something further out. Faint and dashed so the
// boxes that are actually *in* here stay dominant — but present, because an
// inside that hid its own wiring out would be telling half the truth.
// Clicking one leaves: it climbs to wherever that subsystem lives and picks it.
export function ExitBox({ data }: NodeProps) {
  const { label, icon } = data as { label: string; icon: string | null };
  const Icon = icon ? iconFor(icon) : null;
  return (
    <div className="exit-box" title={`${label} — outside this subsystem`}>
      <Handle type="target" position={Position.Top} className="port" />
      {Icon && <Icon size={13} strokeWidth={2} />}
      {label}
      <Handle type="source" position={Position.Bottom} className="port" />
    </div>
  );
}
