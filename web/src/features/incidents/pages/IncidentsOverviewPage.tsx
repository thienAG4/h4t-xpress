// IncidentsOverviewPage - H-04 (Figma "Overview"): counters, priority and type breakdown,
// latest incidents

import { Link } from "react-router";
import { PageHeader } from "@/components/PageHeader";
import { IncidentStatusBadge, PriorityBadge } from "@/components/StatusBadge";
import { Alert, Card, EmptyState, KpiCard, Loading, Table, Td, Th } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatRelative } from "@/lib/format";
import { INCIDENT_TYPE, PRIORITY } from "@/lib/labels";
import type { IncidentPriority, IncidentType } from "@/types";
import { useIncidentList, useIncidentSummary } from "../hooks";

function Bars({ rows }: { rows: { label: string; count: number; color: string }[] }) {
  const max = Math.max(1, ...rows.map((row) => row.count));
  return (
    <ul className="flex flex-col gap-3">
      {rows.map((row) => (
        <li key={row.label} className="grid grid-cols-[9rem_1fr_2rem] items-center gap-3 text-sm">
          <span className="truncate text-neutral-700">{row.label}</span>
          <span className="h-2.5 overflow-hidden rounded-full bg-neutral-100">
            <span className="block h-full rounded-full" style={{ width: `${(row.count / max) * 100}%`, backgroundColor: row.color }} />
          </span>
          <span className="text-right font-semibold">{row.count}</span>
        </li>
      ))}
    </ul>
  );
}

const PRIORITY_COLOR: Record<IncidentPriority | "UNSET", string> = {
  HIGH: "#f8183e",
  MEDIUM: "#f59e0b",
  LOW: "#98a1b3",
  UNSET: "#d4e4fe",
};

const LINK_BUTTON = "inline-flex h-10 items-center rounded-button px-4 text-sm font-semibold";

export function IncidentsOverviewPage() {
  const summary = useIncidentSummary();
  const latest = useIncidentList({ page: 1, page_size: 6 });

  if (summary.isPending) return <Loading />;
  if (summary.isError) return <Alert tone="danger">{errorMessage(summary.error)}</Alert>;
  const data = summary.data;

  const priorities = (["HIGH", "MEDIUM", "LOW", "UNSET"] as const).map((key) => ({
    label: key === "UNSET" ? "Not classified" : PRIORITY[key].label,
    count: data.by_priority[key] ?? 0,
    color: PRIORITY_COLOR[key],
  }));
  const types = Object.entries(data.by_type_30d)
    .sort((a, b) => b[1] - a[1])
    .map(([type, count]) => ({ label: INCIDENT_TYPE[type as IncidentType] ?? type, count, color: "#1070f8" }));

  return (
    <>
      <PageHeader
        title="Incidents overview"
        description="Problems reported by drivers on the road, and what the hub decided."
        actions={
          <>
            <Link to="/hub/incidents/list?open=1" className={`${LINK_BUTTON} bg-primary-600 text-white hover:bg-primary-700`}>
              Active incidents
            </Link>
            <Link to="/hub/incidents/list" className={`${LINK_BUTTON} border border-line bg-white hover:bg-primary-50`}>
              Incident history
            </Link>
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="New" value={data.open} tone={data.open ? "danger" : "neutral"} hint="Waiting for classification" />
        <KpiCard label="In review" value={data.in_review} tone="warning" hint="Classified, solution pending" />
        <KpiCard label="Resolving" value={data.resolving} tone="primary" hint="Waiting for a replacement driver" />
        <KpiCard label="Resolved today" value={data.resolved_today} tone="success" />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card title="Open incidents by priority">
          <Bars rows={priorities} />
        </Card>
        <Card title="Incident types, last 30 days">
          {types.length ? <Bars rows={types} /> : <p className="text-sm text-neutral-600">No incident in the last 30 days.</p>}
        </Card>
      </div>

      <section className="mt-6">
        <h2 className="mb-3 text-base font-semibold">Latest incidents</h2>
        {latest.data?.items.length === 0 && <EmptyState title="No incident reported yet" />}
        {latest.data && latest.data.items.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Incident</Th>
                <Th>Driver</Th>
                <Th>Type</Th>
                <Th>Reported</Th>
                <Th>Priority</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {latest.data.items.map((incident) => (
                <tr key={incident.id} className="hover:bg-neutral-50">
                  <Td>
                    <Link to={`/hub/incidents/${incident.id}`} className="font-semibold hover:text-primary-600">
                      {incident.code}
                    </Link>
                  </Td>
                  <Td>{incident.driver_name}</Td>
                  <Td>{INCIDENT_TYPE[incident.type]}</Td>
                  <Td>{formatRelative(incident.reported_at)}</Td>
                  <Td>
                    <PriorityBadge priority={incident.priority} />
                  </Td>
                  <Td>
                    <IncidentStatusBadge status={incident.status} />
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </section>
    </>
  );
}
