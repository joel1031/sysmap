import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { icons } from 'lucide-react';
import { BOX_SIZE } from './layout';

export interface BoxData {
  label: string;
  color: string;
  sizeStep: 1 | 2 | 3;
  icon: string | null;
  [key: string]: unknown;
}

// The naming step picks icons by their kebab-case Lucide names; the package
// exports them keyed in PascalCase. Unknown names fall back to no icon.
function iconFor(name: string | null) {
  if (!name) return undefined;
  const pascal = name
    .split('-')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join('');
  return icons[pascal as keyof typeof icons];
}

// A subsystem at rest: an icon and a name on a colored card. Nothing else.
export function SubsystemBox({ data }: NodeProps) {
  const { label, color, sizeStep, icon } = data as BoxData;
  const { w, h } = BOX_SIZE[sizeStep];
  const Icon = iconFor(icon);
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
      {Icon && (
        <Icon
          size={sizeStep === 3 ? 22 : sizeStep === 2 ? 19 : 16}
          color={color}
          strokeWidth={2.1}
        />
      )}
      <span>{label}</span>
      <Handle type="source" position={Position.Bottom} className="port" />
    </div>
  );
}
