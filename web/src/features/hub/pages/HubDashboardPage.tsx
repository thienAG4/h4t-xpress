// HubDashboardPage - H-01: today's KPIs, orders by status, what needs attention, order board

import { Link } from "react-router";
import { PageHeader } from "@/components/PageHeader";
import { IncidentStatusBadge, PriorityBadge } from "@/components/StatusBadge";
import { Alert, Card, KpiCard, Loading } from "@/components/ui";
import { useIncidentList } from "@/features/incidents/hooks";
import { errorMessage } from "@/lib/errors";
import { formatClock, formatDay, formatRelative } from "@/lib/format";
import { INCIDENT_TYPE } from "@/lib/labels";
import { OrdersTable } from "../components/OrdersTable";
import { StatusDonut } from "../components/StatusDonut";
import { useDashboard, useHubOrders } from "../hooks";

function NeedsAttention() {
  const risky = useHubOrders({ page: 1, page_size: 5, at_risk: true });
  const incidents = useIncidentList({ page: 1, page_size: 4, open_only: true });

  return (
    <Card title="Needs attention">
      <h3 className="text-xs font-semibold tracking-wide text-neutral-500 uppercase">SLA risk</h3>
      <ul className="mt-2 flex flex-col gap-2">
        {risky.data?.items.length === 0 && <li className="text-sm text-neutral-600">No order is running late.</li>}
        {risky.data?.items.map((order) => (
          <li key={order.id}>
            <Link
              to={`/hub/tracking/${order.id}`}
              className="flex items-center justify-between gap-3 rounded-input bg-danger-50 px-3 py-2 text-sm hover:bg-danger-50/70"
            >
              <span>
                <span className="font-semibold">{order.waybill_code}</span>
                <span className="block text-xs text-neutral-600">{order.driver_name ?? "No driver yet"}</span>
              </span>
              <span className="text-right text-xs text-danger-700">
                Promised {formatClock(order.promised_at)}
                <span className="block">ETA {formatClock(order.current_eta)}</span>
              </span>
            </Link>
          </li>
        ))}
      </ul>

      <h3 className="mt-5 text-xs font-semibold tracking-wide text-neutral-500 uppercase">Open incidents</h3>
      <ul className="mt-2 flex flex-col gap-2">
        {incidents.data?.items.length === 0 && <li className="text-sm text-neutral-600">No open incident.</li>}
        {incidents.data?.items.map((incident) => (
          <li key={incident.id}>
            <Link
              to={`/hub/incidents/${incident.id}`}
              className="flex items-center justify-between gap-3 rounded-input border border-line px-3 py-2 text-sm hover:border-primary-200"
            >
              <span>
                <span className="font-semibold">{incident.code}</span> {INCIDENT_TYPE[incident.type]}
                <span className="block text-xs text-neutral-600">
                  {incident.driver_name} - {formatRelative(incident.reported_at)}
                </span>
              </span>
              <span className="flex flex-col items-end gap-1">
                <IncidentStatusBadge status={incident.status} />
                {incident.priority && <PriorityBadge priority={incident.priority} />}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </Card>
  );
}

export function HubDashboardPage() {
  const dashboard = useDashboard();

  if (dashboard.isPending) return <Loading />;
  if (dashboard.isError) return <Alert tone="danger">{errorMessage(dashboard.error)}</Alert>;
  const data = dashboard.data;
  const onTime = data.on_time_rate_today === null ? "-" : `${Math.round(data.on_time_rate_today * 100)}%`;

  return (
    <>
      <PageHeader title="Hub dashboard" description={`${formatDay(data.date)} - updates live as drivers work.`} />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <KpiCard label="Orders today" value={data.total} hint="Open orders plus the ones closed today" />
        <KpiCard label="SLA risk" value={data.at_risk} tone={data.at_risk ? "danger" : "success"} hint="ETA past the promised time" />
        <KpiCard label="Delivered today" value={data.delivered_today} tone="success" hint={`On time: ${onTime}`} />
        <KpiCard
          label="Open incidents"
          value={data.open_incidents}
          tone={data.high_priority_incidents ? "danger" : "warning"}
          hint={`${data.high_priority_incidents} high priority`}
        />
        <KpiCard label="Drivers online" value={data.drivers_online} tone="primary" hint={`${data.drivers_on_shift} on shift today`} />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[3fr_2fr]">
        <Card title="Orders by status">
          <StatusDonut byStatus={data.by_status} total={data.total} />
        </Card>
        <NeedsAttention />
      </div>

      <section className="mt-6">
        <h2 className="mb-3 text-base font-semibold">Order board</h2>
        <OrdersTable />
      </section>
    </>
  );
}
