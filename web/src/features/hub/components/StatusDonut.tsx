// StatusDonut - orders by status as a ring with a two-column legend (Figma "Loading Vehicles" card)

import { RingChart } from "@/components/RingChart";
import type { OrderStatus } from "@/types";

// Grouped so the ring stays readable. Blues for work in progress as in Figma, then done and problems.
const GROUPS: { label: string; color: string; statuses: OrderStatus[] }[] = [
  { label: "On the road", color: "#0b2a7a", statuses: ["OUT_FOR_DELIVERY"] },
  { label: "With driver", color: "#1070f8", statuses: ["ASSIGNED", "PICKED_UP"] },
  { label: "Waiting", color: "#7fb0fb", statuses: ["AWAITING_ASSIGNMENT", "RESCHEDULED"] },
  { label: "Delivered", color: "#22c55e", statuses: ["DELIVERED"] },
  {
    label: "Hold or failed",
    color: "#e5484d",
    statuses: ["ON_HOLD", "DELIVERY_FAILED", "RETURNING", "RETURNED_TO_HUB", "CANCELLED"],
  },
];

export function StatusDonut({ byStatus, total }: { byStatus: Record<string, number>; total: number }) {
  const groups = GROUPS.map((group) => ({
    ...group,
    count: group.statuses.reduce((sum, status) => sum + (byStatus[status] ?? 0), 0),
  }));

  return (
    <div className="flex flex-wrap items-center gap-6">
      <RingChart parts={groups} centerValue={total} centerLabel="Orders today" />
      <ul className="grid min-w-48 flex-1 grid-cols-2 gap-x-5 gap-y-4">
        {groups.map((group) => (
          <li key={group.label} className="border-l-[3px] pl-3" style={{ borderColor: group.color }}>
            <p className="text-sm text-neutral-600">{group.label}</p>
            <p className="text-lg font-semibold text-ink tabular-nums">{group.count}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
