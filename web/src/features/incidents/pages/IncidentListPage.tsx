// IncidentListPage - H-05 (Figma "View All Incidents"): status tabs, priority filter, cards

import { useState } from "react";
import { Link, useSearchParams } from "react-router";
import { PageHeader } from "@/components/PageHeader";
import { IncidentStatusBadge, PriorityBadge } from "@/components/StatusBadge";
import { Alert, Card, EmptyState, Loading, Pagination, SelectField } from "@/components/ui";
import { cn } from "@/lib/cn";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { INCIDENT_TYPE, PRIORITY, options } from "@/lib/labels";
import type { IncidentPriority, IncidentStatus } from "@/types";
import type { IncidentFilters } from "../api";
import { useIncidentList } from "../hooks";

type Tab = { key: string; label: string; status?: IncidentStatus; open?: boolean };

const TABS: Tab[] = [
  { key: "all", label: "All incidents" },
  { key: "open", label: "Active", open: true },
  { key: "new", label: "New", status: "OPEN" },
  { key: "review", label: "In review", status: "IN_REVIEW" },
  { key: "resolving", label: "Resolving", status: "RESOLVING" },
  { key: "resolved", label: "Resolved", status: "RESOLVED" },
];

const DOT: Record<IncidentStatus, string> = {
  OPEN: "bg-danger-500",
  IN_REVIEW: "bg-warning-500",
  RESOLVING: "bg-primary-600",
  RESOLVED: "bg-success-500",
  CLOSED_NO_ACTION: "bg-neutral-400",
};

const PAGE_SIZE = 8;

export function IncidentListPage() {
  const [params] = useSearchParams();
  const [tab, setTab] = useState(params.get("open") ? "open" : "all");
  const [priority, setPriority] = useState<IncidentPriority | "">("");
  const [page, setPage] = useState(1);
  const current = TABS.find((item) => item.key === tab) ?? TABS[0];
  const filters: IncidentFilters = {
    page,
    page_size: PAGE_SIZE,
    status: current.status,
    open_only: current.open,
    priority: priority || undefined,
  };
  const incidents = useIncidentList(filters);

  return (
    <>
      <PageHeader
        title="View all incidents"
        actions={
          <Link to="/hub/incidents" className="inline-flex h-10 items-center rounded-button border border-line bg-white px-4 text-sm font-semibold">
            Back to overview
          </Link>
        }
      />

      <div className="mb-4 flex flex-wrap items-end justify-between gap-3 border-b border-line">
        <nav className="flex gap-1 overflow-x-auto [scrollbar-width:none]" aria-label="Incident status">
          {TABS.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => {
                setTab(item.key);
                setPage(1);
              }}
              className={cn(
                "border-b-2 px-3 py-2.5 text-sm whitespace-nowrap",
                item.key === tab ? "border-primary-600 font-semibold text-primary-700" : "border-transparent text-neutral-600",
              )}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="mb-2 w-48">
          <SelectField
            compact
            aria-label="Priority"
            placeholder="Any priority"
            options={options(PRIORITY)}
            value={priority}
            onChange={(event) => {
              setPriority(event.target.value as IncidentPriority | "");
              setPage(1);
            }}
          />
        </div>
      </div>

      {incidents.isError && <Alert tone="danger">{errorMessage(incidents.error)}</Alert>}
      {incidents.isPending && <Loading />}
      {incidents.data?.items.length === 0 && <EmptyState title="No incident in this list" />}
      <div className="flex flex-col gap-3">
        {incidents.data?.items.map((incident) => (
          <Card key={incident.id} className="p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className={cn("size-3 rounded-full", DOT[incident.status])} />
                <span className="font-display font-bold">{incident.code}</span>
                <PriorityBadge priority={incident.priority} />
                <IncidentStatusBadge status={incident.status} />
              </div>
              <span className="text-xs text-neutral-500">Posted {formatDateTime(incident.reported_at)}</span>
            </div>
            <p className="mt-2 text-sm font-semibold">
              {INCIDENT_TYPE[incident.type]} - {incident.order_count} parcel{incident.order_count === 1 ? "" : "s"}
            </p>
            <p className="mt-1 line-clamp-2 text-sm text-neutral-600">{incident.description}</p>
            <div className="mt-3 flex items-center justify-between border-t border-line pt-3 text-sm">
              <span className="text-neutral-700">{incident.driver_name}</span>
              <Link to={`/hub/incidents/${incident.id}`} className="font-semibold text-primary-600 underline-offset-4 hover:underline">
                Handle issue
              </Link>
            </div>
          </Card>
        ))}
      </div>
      {incidents.data && incidents.data.total > PAGE_SIZE && (
        <Pagination page={page} pageSize={PAGE_SIZE} total={incidents.data.total} onChange={setPage} />
      )}
    </>
  );
}
