// DriversPanel - left column of H-03 drawn like the Figma "Vehicles" list: search, filter chips,
// one card per driver with a Track button; the tracked driver's card opens to show the stops

import { Phone, Search, Truck } from "lucide-react";
import { useState } from "react";
import { Avatar, EmptyState, Loading, Panel } from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatClock, formatPhone, formatRelative } from "@/lib/format";
import type { DriverRoute, HubDriverRow } from "@/types";
import { useHubDrivers } from "../hooks";

type Filter = "online" | "busy" | "all";

const FILTERS: { value: Filter; label: string; test: (driver: HubDriverRow) => boolean }[] = [
  { value: "online", label: "Taking orders", test: (driver) => driver.availability === "ONLINE" },
  { value: "busy", label: "With orders", test: (driver) => driver.active_orders > 0 },
  { value: "all", label: "All", test: () => true },
];

function presence(driver: HubDriverRow): { label: string; className: string } {
  if (driver.has_pending_offer) return { label: "Answering offer", className: "text-warning-700" };
  if (driver.active_orders > 0) return { label: "On the road", className: "text-warning-700" };
  if (driver.availability === "ONLINE") return { label: "Taking orders", className: "text-success-700" };
  return { label: "Offline", className: "text-neutral-500" };
}

/** Departure, stops and arrival with hollow dots on a line (Figma expanded vehicle card). */
function RouteStops({ route }: { route: DriverRoute }) {
  const rows = [
    { key: "hub", label: "Departure", value: route.hub_name, time: null as string | null },
    ...route.stops.map((stop, index) => ({
      key: stop.id,
      label: index === route.stops.length - 1 ? "Arrival" : `Stop ${String(index + 1).padStart(2, "0")}`,
      value: stop.recipient_name,
      time: stop.eta,
    })),
  ];
  return (
    <ol className="relative mt-3 flex flex-col gap-2 border-t border-dashed border-line pt-3 text-xs">
      {rows.map((row, index) => (
        <li key={row.key} className="flex items-center gap-3">
          <span
            className={cn(
              "size-2 shrink-0 rounded-full border-2",
              index === 0 ? "border-primary-600 bg-primary-600" : "border-primary-600 bg-white",
            )}
            aria-hidden
          />
          <span className="w-16 shrink-0 text-neutral-500">{row.label}</span>
          <span className="min-w-0 flex-1 truncate text-ink">{row.value}</span>
          {row.time && <span className="shrink-0 text-neutral-500 tabular-nums">{formatClock(row.time)}</span>}
        </li>
      ))}
    </ol>
  );
}

type Props = {
  selectedId: string | null;
  onSelect: (driverId: string | null) => void;
  /** Route of the tracked driver, shown inside their card. */
  route?: DriverRoute;
};

export function DriversPanel({ selectedId, onSelect, route }: Props) {
  const drivers = useHubDrivers();
  const [filter, setFilter] = useState<Filter>("busy");
  const [search, setSearch] = useState("");
  const test = FILTERS.find((item) => item.value === filter)?.test ?? (() => true);
  const needle = search.trim().toLowerCase();
  const visible = (drivers.data ?? []).filter(
    (driver) => test(driver) && (!needle || driver.name.toLowerCase().includes(needle) || (driver.phone ?? "").includes(needle)),
  );

  return (
    <Panel
      title="Drivers"
      action={
        <label className="relative">
          <Search className="absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-neutral-400" aria-hidden />
          <input
            type="search"
            aria-label="Search drivers"
            placeholder="Search drivers"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="h-9 w-44 rounded-lg border border-line pr-2 pl-8 text-sm placeholder:text-placeholder focus:border-primary-500 focus:outline-none"
          />
        </label>
      }
      className="min-h-0"
      bodyClassName="flex min-h-0 flex-col gap-3 overflow-y-auto p-3"
    >
      <div className="flex flex-wrap gap-2 px-1">
        {FILTERS.map((item) => (
          <button
            key={item.value}
            type="button"
            onClick={() => setFilter(item.value)}
            aria-pressed={filter === item.value}
            className={cn(
              "rounded-full border px-3 py-1 text-sm",
              filter === item.value ? "border-primary-600 bg-primary-50 text-primary-700" : "border-neutral-300 text-ink hover:border-primary-200",
            )}
          >
            {item.label}
          </button>
        ))}
      </div>
      {drivers.isPending && <Loading />}
      {drivers.data && visible.length === 0 && <EmptyState title="No driver in this list" />}
      {visible.map((driver) => {
        const selected = driver.id === selectedId;
        const state = presence(driver);
        return (
          <article
            key={driver.id}
            className={cn(
              "rounded-lg border bg-white p-3",
              selected ? "border-2 border-primary-600 shadow-sm" : "border-line hover:border-primary-200",
            )}
          >
            <div className="flex items-center gap-3">
              <Truck className="size-7 shrink-0 text-primary-600" strokeWidth={1.75} aria-hidden />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-ink">{driver.name}</p>
                <p className={cn("text-xs", state.className)}>{state.label}</p>
              </div>
              <button
                type="button"
                onClick={() => onSelect(selected ? null : driver.id)}
                aria-label={selected ? `Stop tracking ${driver.name}` : `Track ${driver.name}`}
                className={cn(
                  "flex h-8 items-center gap-1.5 rounded-md border px-2.5 text-sm font-medium",
                  selected ? "border-primary-600 bg-primary-600 text-white" : "border-primary-600 text-primary-700 hover:bg-primary-50",
                )}
              >
                {!selected && <Search className="size-3.5" aria-hidden />}
                {selected ? "Tracking" : "Track"}
              </button>
            </div>
            <div className="mt-2 flex items-center justify-between gap-2 pl-10 text-xs text-neutral-500">
              <span>
                {driver.active_orders} order{driver.active_orders === 1 ? "" : "s"} -{" "}
                {driver.shift_today ? `Shift ${driver.shift_today}` : "No shift today"}
              </span>
              <span>seen {formatRelative(driver.last_seen_at)}</span>
            </div>
            {selected && route && <RouteStops route={route} />}
            {selected && (
              <div className="mt-3 flex items-center gap-3 rounded-md bg-neutral-100 px-3 py-2">
                <Avatar name={driver.name} size="sm" />
                <span className="min-w-0 flex-1 text-xs">
                  <span className="block text-neutral-500">Driver's phone</span>
                  <span className="block font-semibold text-ink">{formatPhone(driver.phone)}</span>
                </span>
                {driver.phone && (
                  <a href={`tel:${driver.phone}`} aria-label={`Call ${driver.name}`} className="text-neutral-600 hover:text-primary-600">
                    <Phone className="size-4" aria-hidden />
                  </a>
                )}
              </div>
            )}
          </article>
        );
      })}
    </Panel>
  );
}
