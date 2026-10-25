// StatusDonut - orders by status as a CSS conic-gradient ring (Figma "Loading Vehicles" card)

import { ORDER_STATUS } from "@/lib/labels";
import type { OrderStatus } from "@/types";

// Grouped so the ring stays readable: waiting, with a driver, done, problems.
const GROUPS: { label: string; color: string; statuses: OrderStatus[] }[] = [
  { label: "Waiting for driver", color: "#f59e0b", statuses: ["AWAITING_ASSIGNMENT", "RESCHEDULED"] },
  { label: "With a driver", color: "#1070f8", statuses: ["ASSIGNED", "PICKED_UP"] },
  { label: "Out for delivery", color: "#0a479f", statuses: ["OUT_FOR_DELIVERY"] },
  { label: "Delivered", color: "#22c55e", statuses: ["DELIVERED"] },
  {
    label: "On hold or failed",
    color: "#f8183e",
    statuses: ["ON_HOLD", "DELIVERY_FAILED", "RETURNING", "RETURNED_TO_HUB", "CANCELLED"],
  },
];

/** One coloured arc per non-empty group, laid end to end around the circle. */
function conicGradient(groups: { color: string; count: number }[], total: number): string {
  const arcs: string[] = [];
  groups
    .filter((group) => group.count > 0)
    .reduce((start, group) => {
      const end = start + (group.count / Math.max(total, 1)) * 360;
      arcs.push(`${group.color} ${start}deg ${end}deg`);
      return end;
    }, 0);
  return arcs.length ? `conic-gradient(${arcs.join(", ")})` : "conic-gradient(#e6e7ee 0deg 360deg)";
}

export function StatusDonut({ byStatus, total }: { byStatus: Record<string, number>; total: number }) {
  const groups = GROUPS.map((group) => ({
    ...group,
    count: group.statuses.reduce((sum, status) => sum + (byStatus[status] ?? 0), 0),
  }));
  const ring = conicGradient(groups, total);

  return (
    <div className="flex flex-wrap items-center gap-6">
      <div className="relative size-40 shrink-0 rounded-full" style={{ background: ring }} role="img" aria-label="Orders by status">
        <div className="absolute inset-5 flex flex-col items-center justify-center rounded-full bg-white">
          <span className="font-display text-3xl font-bold">{total}</span>
          <span className="text-xs text-neutral-600">Orders today</span>
        </div>
      </div>
      <ul className="grid flex-1 grid-cols-2 gap-x-6 gap-y-3">
        {groups.map((group) => (
          <li key={group.label} className="border-l-4 pl-3" style={{ borderColor: group.color }}>
            <p className="text-xs text-neutral-600">{group.label}</p>
            <p className="font-display text-lg font-bold">{group.count}</p>
          </li>
        ))}
      </ul>
      <p className="sr-only">
        {Object.entries(byStatus)
          .map(([status, count]) => `${ORDER_STATUS[status as OrderStatus]?.label ?? status}: ${count}`)
          .join(", ")}
      </p>
    </div>
  );
}
