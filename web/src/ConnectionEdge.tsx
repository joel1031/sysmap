import { BaseEdge, Position, getBezierPath, useInternalNode } from '@xyflow/react';
import type { EdgeProps, InternalNode } from '@xyflow/react';

// The drawn line for one connection. It attaches where its two boxes face
// each other — computed from the boxes' live positions — instead of at fixed
// top/bottom ports, so a line never loops around a box to obey a port.
// Geometry follows React Flow's floating-edges example.
//
// At rest it's a uniform faint track. When active (its box or itself is
// selected), it carries one animated pulse layer per direction, each drifting
// the way that dependency actually points.

export interface Flow {
  color: string; // the leaning subsystem's color
  reverse: boolean; // true when this direction runs against the drawn path
}

function center(node: InternalNode) {
  return {
    x: node.internals.positionAbsolute.x + (node.measured.width ?? 0) / 2,
    y: node.internals.positionAbsolute.y + (node.measured.height ?? 0) / 2,
  };
}

// Where the line from this box's center toward the other box's center leaves
// this box's rectangle.
function exitPoint(node: InternalNode, other: InternalNode) {
  const w = (node.measured.width ?? 0) / 2;
  const h = (node.measured.height ?? 0) / 2;
  const c = center(node);
  const o = center(other);
  const u = (o.x - c.x) / (2 * w) - (o.y - c.y) / (2 * h);
  const v = (o.x - c.x) / (2 * w) + (o.y - c.y) / (2 * h);
  const a = 1 / (Math.abs(u) + Math.abs(v));
  return { x: w * a * (u + v) + c.x, y: h * a * (v - u) + c.y };
}

function sideOf(node: InternalNode, p: { x: number; y: number }): Position {
  const x = node.internals.positionAbsolute.x;
  const y = node.internals.positionAbsolute.y;
  if (p.x <= x + 1) return Position.Left;
  if (p.x >= x + (node.measured.width ?? 0) - 1) return Position.Right;
  if (p.y <= y + 1) return Position.Top;
  return Position.Bottom;
}

export function ConnectionEdge({ id, source, target, data }: EdgeProps) {
  const sourceNode = useInternalNode(source);
  const targetNode = useInternalNode(target);
  if (!sourceNode || !targetNode) return null;

  const s = exitPoint(sourceNode, targetNode);
  const t = exitPoint(targetNode, sourceNode);
  const [path] = getBezierPath({
    sourceX: s.x,
    sourceY: s.y,
    sourcePosition: sideOf(sourceNode, s),
    targetX: t.x,
    targetY: t.y,
    targetPosition: sideOf(targetNode, t),
    curvature: 0.2,
  });

  const flows = (data?.flows ?? []) as Flow[];
  return (
    <>
      <BaseEdge id={id} path={path} />
      {flows.map((f, i) => (
        <path
          key={i}
          className="flow-pulse"
          d={path}
          style={{
            stroke: f.color,
            animationDirection: f.reverse ? 'reverse' : 'normal',
            animationDelay: `${-0.4 * i}s`,
          }}
        />
      ))}
    </>
  );
}
