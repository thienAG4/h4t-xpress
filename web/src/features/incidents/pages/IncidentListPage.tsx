// IncidentListPage - H-05 laid out like the Figma "View All Incidents": search, priority and
// period filters, status tabs with icons, one card per incident, numbered pages

import { CircleCheck, Hourglass, Inbox, LoaderCircle, MailPlus, Search } from "lucide-react";
import { useState } from "react";
import { Link, useSearchParams } from "react-router";
import { PageHeader } from "@/components/PageHeader";
import { IncidentStatusBadge, PriorityBadge } from "@/components/StatusBadge";
import { Alert, Avatar, EmptyState, Loading } from "@/components/ui";
import { cn } from "@/lib/cn";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { INCIDENT_TYPE } from "@/lib/labels";
import type { IncidentPriority, IncidentStatus } from "@/types";
import type { IncidentFilters } from "../api";
import { useIncidentList } from "../hooks";

type Tab = { key: string; label: string; icon: typeof Inbox; status?: IncidentStatus; open?: boolean };

const TABS: Tab[] = [
  { key: "all", label: "All incidents", icon: Inbox },
  { key: "open", label: "Active", icon: Hourglass, open: true },
  { key: "new", label: "New", icon: MailPlus, status: "OPEN" },
  { key: "review", label: "In review", icon: LoaderCircle, status: "IN_REVIEW" },
  { key: "resolving", label: "Resolving", icon: LoaderCircle, status: "RESOLVING" },
  { key: "resolved", label: "Resolved", icon: CircleCheck, status: "RESOLVED" },
];

// Figma: a coloured dot before each incident code, by status.
const DOT: Record<IncidentStatus, string> = {
  OPEN: "bg-primary-500",
  IN_REVIEW: "bg-[#f8c47a]",
  RESOLVING: "bg-warning-500",
  RESOLVED: "bg-success-500",
  CLOSED_NO_ACTION: "bg-neutral-400",
};

const PERIODS = [
  { value: "", label: "Any time" },
  { value: "1", label: "Today" },
  { value: "7", label: "This week" },
  { value: "30", label: "This month" },
];

const PRIORITIES: { value: IncidentPriority | ""; label: string; dot: string }[] = [
  { value: "", label: "Any priority", dot: "bg-neutral-300" },
  { value: "HIGH", label: "High priority", dot: "bg-danger-500" },
  { value: "MEDIUM", label: "Medium priority", dot: "bg-warning-500" },
  { value: "LOW", label: "Low priority", dot: "bg-success-500" },
];

const CONTROL = "h-11 rounded-lg border border-line bg-white px-3 text-sm text-neutral-700 focus:border-primary-500 focus:outline-none";
const PAGE_SIZE = 8;

function PageButtons({ page, total, onChange }: { page: number; total: number; onChange: (page: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (pages < 2) return null;
  const numbers = Array.from({ length: pages }, (_, index) => index + 1).filter(
    (number) => number === 1 || number === pages || Math.abs(number - page) <= 1,
  );
  return (
    <nav className="mt-5 flex items-center justify-end gap-2 text-sm" aria-label="Pages">
      <button type="button" className="px-3 py-2 text-neutral-500 disabled:opacity-40" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        Previous
      </button>
      {numbers.map((number, index) => (
        <span key={number} className="flex items-center gap-2">
          {index > 0 && number - numbers[index - 1] > 1 && <span className="text-neutral-400">...</span>}
          <button
            type="button"
            aria-current={number === page ? "page" : undefined}
            onClick={() => onChange(number)}
            className={cn(
              "grid size-9 place-items-center rounded-md border",
              number === page ? "border-primary-600 bg-primary-600 text-white" : "border-line bg-white text-ink hover:border-primary-200",
            )}
          >
            {number}
          </button>
        </span>
      ))}
      <button type="button" className="px-3 py-2 text-neutral-700 disabled:opacity-40" disabled={page >= pages} onClick={() => onChange(page + 1)}>
        Next
      </button>
    </nav>
  );
}

export function IncidentListPage() {
  const [params] = useSearchParams();
  const [tab, setTab] = useState(params.get("open") ? "open" : "all");
  const [priority, setPriority] = useState<IncidentPriority | "">("");
  const [period, setPeriod] = useState("");
  const [text, setText] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const current = TABS.find((item) => item.key === tab) ?? TABS[0];
  const filters: IncidentFilters = {
    page,
    page_size: PAGE_SIZE,
    status: current.status,
    open_only: current.open,
    priority: priority || undefined,
    q: query || undefined,
    days: period ? Number(period) : undefined,
  };
  const incidents = useIncidentList(filters);
  const reset = () => setPage(1);

  return (
    <>
      <PageHeader title="View all incidents" />

      {/* A div, not a section: each incident card is the section (tests and screen readers). */}
      <div className="rounded-lg border border-line bg-white px-5 pt-5 pb-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <form
            role="search"
            className="relative w-full max-w-xs"
            onSubmit={(event) => {
              event.preventDefault();
              setQuery(text.trim());
              reset();
            }}
          >
            <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-neutral-400" aria-hidden />
            <input
              type="search"
              aria-label="Search incidents"
              placeholder="Search incident, driver or waybill"
              value={text}
              onChange={(event) => setText(event.target.value)}
              className={cn(CONTROL, "w-full bg-neutral-50 pl-9")}
            />
          </form>
          <div className="flex flex-wrap items-center gap-2">
            <label className="relative">
              <span className={cn("absolute top-1/2 left-3 size-2.5 -translate-y-1/2 rounded-full", PRIORITIES.find((item) => item.value === priority)?.dot)} aria-hidden />
              <select
                aria-label="Priority"
                className={cn(CONTROL, "pl-8")}
                value={priority}
                onChange={(event) => {
                  setPriority(event.target.value as IncidentPriority | "");
                  reset();
                }}
              >
                {PRIORITIES.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <select
              aria-label="Period"
              className={CONTROL}
              value={period}
              onChange={(event) => {
                setPeriod(event.target.value);
                reset();
              }}
            >
              {PERIODS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
            <Link to="/hub/incidents" className="inline-flex h-11 items-center rounded-lg bg-primary-600 px-6 text-sm font-semibold text-white hover:bg-primary-700">
              Back
            </Link>
          </div>
        </div>

        <nav className="mt-5 flex gap-2 overflow-x-auto border-b border-line [scrollbar-width:none]" aria-label="Incident status">
          {TABS.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => {
                  setTab(item.key);
                  reset();
                }}
                className={cn(
                  "flex items-center gap-2 border-b-2 px-4 py-3 text-sm whitespace-nowrap",
                  item.key === tab ? "border-primary-600 font-medium text-primary-700" : "border-transparent text-neutral-600 hover:text-ink",
                )}
              >
                <Icon className="size-4" aria-hidden />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="mt-5">
          {incidents.isError && <Alert tone="danger">{errorMessage(incidents.error)}</Alert>}
          {incidents.isPending && <Loading />}
          {incidents.data?.items.length === 0 && <EmptyState title="No incident in this list" />}
          <div className="flex flex-col gap-4">
            {incidents.data?.items.map((incident) => (
              <section key={incident.id} className="rounded-lg border border-line bg-white px-5 pt-4 pb-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className={cn("size-5 rounded-full", DOT[incident.status])} aria-hidden />
                    <span className="text-lg font-medium text-ink">{incident.code}</span>
                    <PriorityBadge priority={incident.priority} />
                    <IncidentStatusBadge status={incident.status} />
                  </div>
                  <span className="text-sm text-neutral-500">Posted at {formatDateTime(incident.reported_at)}</span>
                </div>
                <p className="mt-3 text-[15px] text-ink">
                  {INCIDENT_TYPE[incident.type]}: {incident.order_count} parcel{incident.order_count === 1 ? "" : "s"} affected
                </p>
                <p className="mt-2 line-clamp-2 text-sm text-neutral-600">{incident.description}</p>
                <div className="mt-3 flex items-center justify-between border-t border-line pt-3 text-sm">
                  <span className="flex items-center gap-2.5 text-neutral-700">
                    <Avatar name={incident.driver_name} size="sm" />
                    {incident.driver_name}
                  </span>
                  <Link to={`/hub/incidents/${incident.id}`} className="font-medium text-primary-600 underline underline-offset-4">
                    Handle issue
                  </Link>
                </div>
              </section>
            ))}
          </div>
          {incidents.data && <PageButtons page={page} total={incidents.data.total} onChange={setPage} />}
        </div>
      </div>
    </>
  );
}
