// DriversPanel - left column of H-03 (Figma "Vehicles"): drivers with load, shift and presence

import { useState } from "react";
import { Badge, Button, EmptyState, Loading } from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatPhone, formatRelative } from "@/lib/format";
import type { HubDriverRow } from "@/types";
import { useHubDrivers } from "../hooks";

type Filter = "online" | "busy" | "all";

const FILTERS: { value: Filter; label: string; test: (driver: HubDriverRow) => boolean }[] = [
  { value: "online", label: "Online", test: (driver) => driver.availability === "ONLINE" },
  { value: "busy", label: "With orders", test: (driver) => driver.active_orders > 0 },
  { value: "all", label: "All", test: () => true },
];

type Props = { selectedId: string | null; onSelect: (driverId: string | null) => void };

export function DriversPanel({ selectedId, onSelect }: Props) {
  const drivers = useHubDrivers();
  const [filter, setFilter] = useState<Filter>("online");
  const test = FILTERS.find((item) => item.value === filter)?.test ?? (() => true);
  const visible = (drivers.data ?? []).filter(test);

  return (
    <section className="flex min-h-0 flex-col rounded-card border border-line bg-white">
      <header className="border-b border-line p-4">
        <h2 className="text-base font-semibold">Drivers</h2>
        <div className="mt-3 flex gap-2">
          {FILTERS.map((item) => (
            <button
              key={item.value}
              type="button"
              onClick={() => setFilter(item.value)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium",
                filter === item.value ? "border-primary-600 bg-primary-50 text-primary-700" : "border-line text-neutral-600",
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
      </header>
      <div className="flex flex-col gap-3 overflow-y-auto p-3">
        {drivers.isPending && <Loading />}
        {drivers.data && visible.length === 0 && <EmptyState title="No driver in this list" />}
        {visible.map((driver) => {
          const selected = driver.id === selectedId;
          return (
            <article
              key={driver.id}
              className={cn("rounded-card border p-3", selected ? "border-primary-600 ring-1 ring-primary-600" : "border-line")}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate font-semibold">{driver.name}</p>
                  <p className="text-xs text-neutral-600">{formatPhone(driver.phone)}</p>
                </div>
                <Button size="sm" variant={selected ? "primary" : "secondary"} onClick={() => onSelect(selected ? null : driver.id)}>
                  {selected ? "Tracking" : "Track"}
                </Button>
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Badge tone={driver.availability === "ONLINE" ? "success" : "neutral"}>
                  {driver.availability === "ONLINE" ? "Online" : "Offline"}
                </Badge>
                <Badge tone="primary">
                  {driver.active_orders} order{driver.active_orders === 1 ? "" : "s"}
                </Badge>
                {driver.has_pending_offer && <Badge tone="warning">Answering offer</Badge>}
              </div>
              <p className="mt-2 text-xs text-neutral-500">
                {driver.shift_today ? `Shift: ${driver.shift_today}` : "No shift today"} - seen{" "}
                {formatRelative(driver.last_seen_at)}
              </p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
