import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { BOX_SIZE } from './layout';

export interface BoxData {
  label: string;
  color: string;
  sizeStep: 1 | 2 | 3;
  [key: string]: unknown;
}

// A subsystem at rest: a name on a colored card. Nothing else.
export function SubsystemBox({ data }: NodeProps) {
  const { label, color, sizeStep } = data as BoxData;
  const { w, h } = BOX_SIZE[sizeStep];
  return (
    <div
      className="subsystem-box"
      style={{
        width: w,
        height: h,
        background: `color-mix(in srgb, ${color} var(--box-tint), var(--box-base))`,
        borderColor: color,
        boxShadow: `0 0 var(--glow) color-mix(in srgb, ${color} 35%, transparent)`,
        fontSize: sizeStep === 3 ? 16 : sizeStep === 2 ? 14 : 12.5,
      }}
    >
      <Handle type="target" position={Position.Top} className="port" />
      <span>{label}</span>
      <Handle type="source" position={Position.Bottom} className="port" />
    </div>
  );
}
