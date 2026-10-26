// IncidentsOverviewPage - H-04 laid out like the Figma "Overview": four counters, open incidents
// by priority as a ring, drivers on the map, drivers online, incident types and the latest incidents

import { CircleDot, ClipboardCheck, Hourglass, Siren } from "lucide-react";
import { Link } from "react-router";
import { MapView, type MapPoint } from "@/components/MapView";
import { PageHeader } from "@/components/PageHeader";
import { RingChart } from "@/components/RingChart";
import { IncidentStatusBadge, PriorityBadge } from "@/components/StatusBadge";
import { Alert, Avatar, EmptyState, Loading, Panel, PanelLink, StatCard } from "@/components/ui";
import { useHubDrivers } from "@/features/hub/hooks";
import { errorMessage } from "@/lib/errors";
import { formatRelative } from "@/lib/format";
import { INCIDENT_TYPE, PRIORITY } from "@/lib/labels";
import type { IncidentPriority, IncidentType } from "@/types";
import { useIncidentList, useIncidentSummary } from "../hooks";

const PRIORITY_COLOR: Record<IncidentPriority | "UNSET", string> = {
  HIGH: "#e5484d",
  MEDIUM: "#f5b301",
  LOW: "#22a06b",
  UNSET: "#98a1b3",
};

const LINK_BUTTON = "inline-flex h-11 items-center rounded-lg px-5 text-sm font-semibold";

function Bars({ rows }: { rows: { label: string; count: number }[] }) {
  const max = Math.max(1, ...rows.map((row) => row.count));
  return (
    <ul className="flex flex-col gap-3">
      {rows.map((row) => (
        <li key={row.label} className="grid grid-cols-[10rem_1fr_2rem] items-center gap-3 text-sm">
          <span className="truncate text-neutral-700">{row.label}</span>
          <span className="h-2 overflow-hidden rounded-full bg-primary-50">
            <span className="block h-full rounded-full bg-primary-600" style={{ width: `${(row.count / max) * 100}%` }} />
          </span>
          <span className="text-right font-semibold tabular-nums">{row.count}</span>
        </li>
      ))}
    </ul>
  );
}

/** Figma "Reach": how many drivers are out, and where they are now. */
function DriversMap() {
  const drivers = useHubDrivers();
  const visible = (drivers.data ?? []).filter((driver) => driver.lat !== null && driver.lng !== null && (driver.availability === "ONLINE" || driver.active_orders > 0));
  const points: MapPoint[] = visible.map((driver) => ({
    id: driver.id,
    lat: driver.lat ?? 0,
    lng: driver.lng ?? 0,
    label: `${driver.name} - ${driver.active_orders} orders`,
    kind: "driver",
  }));
  const onRoad = visible.filter((driver) => driver.active_orders > 0).length;
  return (
    <Panel title="Drivers on the road" action={<PanelLink to="/hub/tracking">Live map</PanelLink>} bodyClassName="grid grid-cols-[110px_1fr] items-end gap-4">
      <div>
        <p className="text-4xl font-semibold text-ink tabular-nums">{onRoad}</p>
        <p className="text-sm text-neutral-600">with parcels now</p>
      </div>
      <MapView points={points} className="h-52 rounded-lg" />
    </Panel>
  );
}

/** Figma "Member online": people the hub can reach right now. */
function DriversOnline() {
  const drivers = useHubDrivers();
  const online = (drivers.data ?? []).filter((driver) => driver.availability === "ONLINE" || driver.active_orders > 0).slice(0, 5);
  return (
    <Panel title="Drivers online" bodyClassName="flex flex-col gap-4">
      {drivers.data && online.length === 0 && <p className="text-sm text-neutral-600">Nobody is online right now.</p>}
      {online.map((driver) => (
        <div key={driver.id} className="flex items-center gap-3">
          <Avatar name={driver.name} size="lg" />
          <div className="min-w-0">
            <p className="truncate font-medium text-ink">{driver.name}</p>
            <p className="text-sm text-neutral-600">
              {driver.active_orders > 0 ? `${driver.active_orders} parcels on board` : "Taking orders"}
            </p>
          </div>
        </div>
      ))}
    </Panel>
  );
}

export function IncidentsOverviewPage() {
  const summary = useIncidentSummary();
  const latest = useIncidentList({ page: 1, page_size: 6 });

  if (summary.isPending) return <Loading />;
  if (summary.isError) return <Alert tone="danger">{errorMessage(summary.error)}</Alert>;
  const data = summary.data;

  const priorities = (["HIGH", "MEDIUM", "LOW", "UNSET"] as const).map((key) => ({
    label: key === "UNSET" ? "Not classified" : `${PRIORITY[key].label} priority`,
    count: data.by_priority[key] ?? 0,
    color: PRIORITY_COLOR[key],
  }));
  const openTotal = priorities.reduce((sum, part) => sum + part.count, 0);
  const types = Object.entries(data.by_type_30d)
    .sort((a, b) => b[1] - a[1])
    .map(([type, count]) => ({ label: INCIDENT_TYPE[type as IncidentType] ?? type, count }));

  return (
    <>
      <PageHeader
        title="Overview"
        description="Problems reported by drivers on the road, and what the hub decided."
        actions={
          <>
            <Link to="/hub/incidents/list?open=1" className={`${LINK_BUTTON} bg-primary-600 text-white hover:bg-primary-700`}>
              Active incidents
            </Link>
            <Link to="/hub/incidents/list" className={`${LINK_BUTTON} bg-primary-100 text-primary-700 hover:bg-primary-200`}>
              Incident history
            </Link>
          </>
        }
      />

      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="New" value={data.open} icon={Siren} tone={data.open ? "danger" : "neutral"} hint="Waiting for classification" />
        <StatCard label="In review" value={data.in_review} icon={Hourglass} tone="warning" hint="Classified, solution pending" />
        <StatCard label="Resolving" value={data.resolving} icon={CircleDot} tone="primary" hint="Replacement driver on the way" />
        <StatCard label="Resolved today" value={data.resolved_today} icon={ClipboardCheck} tone="success" hint="Closed since midnight" />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <Panel title="Open incidents" action={<span className="text-sm text-neutral-500">By priority</span>} bodyClassName="flex flex-wrap items-center justify-between gap-6">
          <ul className="flex flex-col gap-3 text-sm">
            {priorities.map((part) => (
              <li key={part.label} className="flex items-center gap-2.5">
                <span className="size-3 rounded-full" style={{ backgroundColor: part.color }} aria-hidden />
                <span className="text-neutral-700">{part.label}</span>
                <span className="font-semibold text-ink tabular-nums">{part.count}</span>
              </li>
            ))}
          </ul>
          <RingChart parts={priorities} centerValue={openTotal} centerLabel="Incidents" />
        </Panel>
        <DriversMap />
        <DriversOnline />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <Panel title="Incident types" action={<span className="text-sm text-neutral-500">Last 30 days</span>}>
          {types.length ? <Bars rows={types} /> : <p className="text-sm text-neutral-600">No incident in the last 30 days.</p>}
        </Panel>
        <Panel title="Latest incidents" action={<PanelLink to="/hub/incidents/list" />}>
          {latest.data?.items.length === 0 && <EmptyState title="No incident reported yet" />}
          {latest.data && latest.data.items.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] border-separate border-spacing-0 text-left text-sm">
                <thead>
                  {/* Warm header band as in the Figma "Latest Order" table. */}
                  <tr className="text-[#6b3b2a]">
                    {["Incident", "Driver", "Type", "Reported", "Priority", "Status"].map((label, index, all) => (
                      <th
                        key={label}
                        scope="col"
                        className={`bg-[#fff1ec] px-4 py-3 font-medium ${index === 0 ? "rounded-l-lg" : ""} ${index === all.length - 1 ? "rounded-r-lg" : ""}`}
                      >
                        {label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {latest.data.items.map((incident) => (
                    <tr key={incident.id} className="hover:bg-neutral-50">
                      <td className="border-b border-line px-4 py-3.5">
                        <Link to={`/hub/incidents/${incident.id}`} className="font-medium text-ink hover:text-primary-600">
                          {incident.code}
                        </Link>
                      </td>
                      <td className="border-b border-line px-4 py-3.5">{incident.driver_name}</td>
                      <td className="border-b border-line px-4 py-3.5">{INCIDENT_TYPE[incident.type]}</td>
                      <td className="border-b border-line px-4 py-3.5 text-neutral-600">{formatRelative(incident.reported_at)}</td>
                      <td className="border-b border-line px-4 py-3.5">
                        <PriorityBadge priority={incident.priority} />
                      </td>
                      <td className="border-b border-line px-4 py-3.5">
                        <IncidentStatusBadge status={incident.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}
