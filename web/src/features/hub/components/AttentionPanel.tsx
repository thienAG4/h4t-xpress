// AttentionPanel - right column of the dashboard, drawn like the Figma "Order Requests" cards:
// orders running late (SLA risk) and incidents still open

import { CircleAlert, Package } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { IncidentStatusBadge, PriorityBadge } from "@/components/StatusBadge";
import { IconTile, Panel } from "@/components/ui";
import { useIncidentList } from "@/features/incidents/hooks";
import { formatClock, formatDateTime, formatRelative } from "@/lib/format";
import { INCIDENT_TYPE } from "@/lib/labels";
import { useHubOrders } from "../hooks";

/** Pickup and destination joined by a dotted line, as in the Figma request card. */
function Leg({ from, fromLabel, to, toLabel }: { from: ReactNode; fromLabel: string; to: ReactNode; toLabel: string }) {
  return (
    <div className="relative pl-5 text-sm">
      <span className="absolute top-1.5 left-1 size-2 rounded-full bg-primary-600" aria-hidden />
      <span className="absolute top-4 bottom-6 left-[7px] border-l border-dashed border-primary-300" aria-hidden />
      <span className="absolute bottom-[26px] left-0.5 size-2.5 rounded-full border-2 border-primary-600 bg-white" aria-hidden />
      <p className="text-xs text-neutral-500">{fromLabel}</p>
      <p className="truncate font-medium text-ink">{from}</p>
      <p className="mt-2 text-xs text-neutral-500">{toLabel}</p>
      <p className="truncate font-medium text-ink">{to}</p>
    </div>
  );
}

function RequestCard({
  to,
  icon,
  code,
  when,
  children,
  footer,
  link,
}: {
  to: string;
  icon: typeof Package;
  code: string;
  when: string;
  children: ReactNode;
  footer: ReactNode;
  link: string;
}) {
  return (
    <li>
      <Link to={to} className="block rounded-lg bg-[#fdf1f1] p-2 transition-shadow hover:shadow-md">
        <div className="flex items-center gap-3 rounded-md bg-white/70 px-3 py-2">
          <IconTile icon={icon} size="sm" />
          <span className="font-semibold text-ink">{code}</span>
          <span className="ml-auto text-xs text-neutral-600">{when}</span>
        </div>
        <div className="mx-1 mt-2 rounded-md border border-dashed border-[#f3c7c7] bg-white/40 px-3 py-3">{children}</div>
        <div className="mt-2 flex items-center justify-between gap-2 px-2 pb-1 text-sm">
          <span className="min-w-0 truncate">{footer}</span>
          <span className="shrink-0 font-medium text-primary-600">{link}</span>
        </div>
      </Link>
    </li>
  );
}

export function AttentionPanel({ className }: { className?: string }) {
  const risky = useHubOrders({ page: 1, page_size: 4, at_risk: true });
  const incidents = useIncidentList({ page: 1, page_size: 4, open_only: true });

  return (
    <Panel title="Needs attention" className={className} bodyClassName="flex flex-col gap-6">
      <section aria-labelledby="sla-risk">
        <h3 id="sla-risk" className="mb-3 flex items-center justify-between font-sans text-sm text-neutral-600">
          Orders at SLA risk
          <span className="font-semibold text-ink">{risky.data?.total ?? 0}</span>
        </h3>
        {risky.data?.items.length === 0 && <p className="text-sm text-neutral-600">No order is running late.</p>}
        <ul className="flex flex-col gap-3">
          {risky.data?.items.map((order) => (
            <RequestCard
              key={order.id}
              to={`/hub/tracking/${order.id}`}
              icon={Package}
              code={order.waybill_code}
              when={`Promised ${formatDateTime(order.promised_at)}`}
              footer={<span className="text-danger-700">ETA {formatClock(order.current_eta)}</span>}
              link="View details"
            >
              <Leg
                fromLabel="Driver"
                from={order.driver_name ?? "No driver yet"}
                toLabel="Destination"
                to={`${order.recipient_name} - ${order.delivery_address}`}
              />
            </RequestCard>
          ))}
        </ul>
      </section>

      <section aria-labelledby="open-incidents">
        <h3 id="open-incidents" className="mb-3 flex items-center justify-between font-sans text-sm text-neutral-600">
          Open incidents
          <span className="font-semibold text-ink">{incidents.data?.total ?? 0}</span>
        </h3>
        {incidents.data?.items.length === 0 && <p className="text-sm text-neutral-600">No open incident.</p>}
        <ul className="flex flex-col gap-3">
          {incidents.data?.items.map((incident) => (
            <RequestCard
              key={incident.id}
              to={`/hub/incidents/${incident.id}`}
              icon={CircleAlert}
              code={incident.code}
              when={formatRelative(incident.reported_at)}
              footer={
                <span className="flex gap-1.5">
                  <IncidentStatusBadge status={incident.status} />
                  {incident.priority && <PriorityBadge priority={incident.priority} />}
                </span>
              }
              link="Handle issue"
            >
              <Leg
                fromLabel="Driver"
                from={incident.driver_name}
                toLabel="Problem"
                to={INCIDENT_TYPE[incident.type]}
              />
            </RequestCard>
          ))}
        </ul>
      </section>
    </Panel>
  );
}
