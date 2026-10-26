// Dashboard lists - the two bottom cards of the Figma hub dashboard ("Unloading Cargo",
// "Available Cargo") filled with orders waiting for a driver and routes in progress

import { Send, UserPlus } from "lucide-react";
import { Link } from "react-router";
import { Badge, Panel, PanelLink } from "@/components/ui";
import { formatClock, formatDateTime } from "@/lib/format";
import { useHubOrders, useRoutes } from "../hooks";

const ROW_BUTTON =
  "grid size-9 shrink-0 place-items-center rounded-lg border border-line text-neutral-600 hover:border-primary-200 hover:text-primary-600";

export function WaitingOrdersPanel({ hubName }: { hubName: string }) {
  const orders = useHubOrders({ page: 1, page_size: 4, status: "AWAITING_ASSIGNMENT" });
  return (
    <Panel title="Waiting for a driver" action={<PanelLink to="/hub/tracking" />} bodyClassName="p-0">
      {orders.data?.items.length === 0 && <p className="px-5 py-6 text-sm text-neutral-600">Every order has a driver.</p>}
      <ul>
        {orders.data?.items.map((order) => (
          <li key={order.id} className="flex items-center gap-3 border-b border-line px-5 py-3 text-sm last:border-b-0">
            <span className="min-w-0 flex-1">
              <span className="block font-medium text-ink">{order.waybill_code}</span>
              <span className="mt-0.5 flex items-center gap-2 text-xs text-neutral-600">
                <span className="truncate">{hubName}</span>
                <span className="flex shrink-0 items-center" aria-hidden>
                  <span className="w-3 border-t border-dashed border-neutral-400" />
                  <span className="size-2 rounded-full border-2 border-primary-600" />
                  <span className="w-3 border-t border-dashed border-neutral-400" />
                </span>
                <span className="truncate">{order.recipient_name}</span>
              </span>
            </span>
            <Badge tone={order.priority === "EXPRESS" ? "danger" : "warning"}>
              {order.priority === "EXPRESS" ? "Express" : "Waiting"}
            </Badge>
            <span className="w-24 shrink-0 text-right text-xs text-neutral-600">
              Promised
              <span className="block text-sm text-ink">{formatDateTime(order.promised_at)}</span>
            </span>
            <Link to={`/hub/tracking/${order.id}`} className={ROW_BUTTON} aria-label={`Choose a driver for ${order.waybill_code}`}>
              <UserPlus className="size-4" aria-hidden />
            </Link>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

export function RouteProgressPanel() {
  const routes = useRoutes();
  const active = routes.data?.filter((route) => route.stops_pending > 0).slice(0, 4) ?? [];
  return (
    <Panel title="Routes in progress" action={<PanelLink to="/hub/routes" />} bodyClassName="p-0">
      {routes.data && active.length === 0 && <p className="px-5 py-6 text-sm text-neutral-600">No driver is on the road.</p>}
      <ul>
        {active.map((route) => {
          const done = route.stops_total - route.stops_pending;
          const share = route.stops_total ? Math.round((done / route.stops_total) * 100) : 0;
          return (
            <li key={route.id} className="flex items-center gap-3 border-b border-line px-5 py-3 text-sm last:border-b-0">
              <span className="w-32 shrink-0">
                <span className="block truncate font-medium text-ink">{route.driver_name}</span>
                <span className="block text-xs text-neutral-600">
                  {done} of {route.stops_total} stops done
                </span>
              </span>
              <span className="flex min-w-0 flex-1 items-center gap-2" aria-label={`${share}% done`}>
                <span className="h-2 flex-1 rounded-full bg-neutral-200">
                  <span className="block h-2 rounded-full bg-primary-600" style={{ width: `${Math.max(share, 4)}%` }} />
                </span>
                <span className="w-9 text-right font-medium text-primary-700 tabular-nums">{share}%</span>
              </span>
              <span className="w-16 shrink-0 text-right text-xs text-neutral-600">
                Next stop
                <span className="block text-sm text-ink">{formatClock(route.next_eta)}</span>
              </span>
              <Link to="/hub/tracking" className={ROW_BUTTON} aria-label={`Track ${route.driver_name}`}>
                <Send className="size-4" aria-hidden />
              </Link>
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}
