// RecentOrdersPanel - Figma "Recent Orders": today's counters, the change against the previous
// 30 days and the orders created per day over the last 30 days (from the hub's report)

import { useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, ClipboardList, FileCheck, FileClock } from "lucide-react";
import type { ReactNode } from "react";
import { IconTile, Panel } from "@/components/ui";
import { fetchReport, type ReportFilters } from "@/features/reports/api";
import { AreaChart } from "@/features/reports/components/charts";
import { cn } from "@/lib/cn";
import { businessDate } from "@/lib/format";
import { hasPermission, useSession } from "@/lib/session";
import type { HubDashboard } from "@/types";

function Counter({ icon, label, value }: { icon: typeof ClipboardList; label: string; value: ReactNode }) {
  return (
    <li className="flex items-center gap-2.5">
      <IconTile icon={icon} size="sm" />
      <span>
        <span className="block text-[13px] whitespace-nowrap text-neutral-600">{label}</span>
        <span className="block text-base font-semibold text-ink tabular-nums">{value}</span>
      </span>
    </li>
  );
}

export function RecentOrdersPanel({ dashboard, className }: { dashboard: HubDashboard; className?: string }) {
  const user = useSession((state) => state.user);
  const filters: ReportFilters = { date_from: businessDate(-29), date_to: businessDate(0), hub_ids: [] };
  const report = useQuery({
    queryKey: ["reports", filters],
    queryFn: () => fetchReport(filters),
    enabled: hasPermission(user, "report.view"),
  });
  const waiting = (dashboard.by_status.AWAITING_ASSIGNMENT ?? 0) + (dashboard.by_status.RESCHEDULED ?? 0);
  const total = report.data?.summary.total_orders;
  const change =
    total?.value != null && total.previous ? Math.round(((total.value - total.previous) / total.previous) * 100) : null;

  return (
    <Panel title="Recent orders" action={<span className="text-sm text-neutral-500">Last 30 days</span>} className={className}>
      <div className="grid gap-4 sm:grid-cols-[124px_minmax(0,1fr)]">
        <div className="flex flex-col justify-between gap-5">
          <ul className="flex flex-col gap-4">
            <Counter icon={ClipboardList} label="Orders today" value={dashboard.total} />
            <Counter icon={FileClock} label="Waiting" value={waiting} />
            <Counter icon={FileCheck} label="Delivered" value={dashboard.delivered_today} />
          </ul>
          {change !== null && (
            <div>
              <p className="text-xs text-neutral-500">Compared with the 30 days before</p>
              <p
                className={cn(
                  "mt-1 flex items-center gap-1 text-2xl font-semibold tabular-nums",
                  change >= 0 ? "text-success-700" : "text-danger-700",
                )}
              >
                {change >= 0 ? <ArrowUp className="size-5" aria-hidden /> : <ArrowDown className="size-5" aria-hidden />}
                {Math.abs(change)}%
              </p>
            </div>
          )}
        </div>
        <div className="min-w-0 rounded-lg border border-line p-2">
          {report.data ? (
            <AreaChart
              label="Orders created"
              points={report.data.volume.map((point) => ({ label: point.label, value: point.orders }))}
            />
          ) : (
            <p className="py-16 text-center text-sm text-neutral-500">
              {report.isError ? "The order history is not available." : "Loading the last 30 days..."}
            </p>
          )}
        </div>
      </div>
    </Panel>
  );
}
