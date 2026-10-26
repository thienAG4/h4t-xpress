// RoutePlanningPage - H-02 laid out like the Figma "Lên kế hoạch tuyến đường": a large road map
// with today's drivers floating on the left and the route summary at the bottom, and the stop
// list on the right. The road network can suggest the fastest order; saving sends it to the driver.

import { Search, Send, Sparkles, Truck } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router";
import { MapView } from "@/components/MapView";
import { OrderStatusBadge } from "@/components/StatusBadge";
import { StopOrderList, type EditorStop } from "@/components/StopOrderEditor";
import { Alert, Badge, Button, EmptyState, Loading, Panel } from "@/components/ui";
import { cn } from "@/lib/cn";
import { errorMessage } from "@/lib/errors";
import { formatClock, formatPhone } from "@/lib/format";
import type { LatLng } from "@/lib/polyline";
import { stopOrderMap } from "@/lib/stopOrder";
import type { OptimizeResult, RouteDetail, RouteSummary } from "@/types";
import { useOptimizeRoute, useRouteDetail, useRoutes, useSaveStopOrder } from "../hooks";

function km(meters: number | null): string {
  return meters === null ? "-" : `${(meters / 1000).toFixed(1)} km`;
}

function duration(seconds: number | null): string {
  if (seconds === null) return "-";
  const minutes = Math.round(seconds / 60);
  return minutes >= 60 ? `${Math.floor(minutes / 60)} h ${minutes % 60} min` : `${minutes} min`;
}

/** Floating list of today's routes (Figma "Vehicles" over the map). */
function RouteList({
  routes,
  selectedId,
  onSelect,
}: {
  routes: RouteSummary[];
  selectedId: string | null;
  onSelect: (routeId: string) => void;
}) {
  const [search, setSearch] = useState("");
  const needle = search.trim().toLowerCase();
  const visible = routes.filter((route) => !needle || route.driver_name.toLowerCase().includes(needle));
  return (
    <div className="flex min-h-0 flex-col rounded-lg bg-white shadow-lg">
      <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
        <h2 className="font-sans text-base font-medium text-ink">Drivers</h2>
        <label className="relative">
          <Search className="absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-neutral-400" aria-hidden />
          <input
            type="search"
            aria-label="Search routes by driver"
            placeholder="Search drivers"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="h-8 w-40 rounded-md border border-line pr-2 pl-8 text-sm placeholder:text-placeholder focus:border-primary-500 focus:outline-none"
          />
        </label>
      </div>
      <ul className="flex min-h-0 flex-col gap-2 overflow-y-auto p-2">
        {visible.length === 0 && <li className="px-2 py-4 text-sm text-neutral-600">No route matches.</li>}
        {visible.map((route) => {
          const selected = route.id === selectedId;
          return (
            <li
              key={route.id}
              className={cn("rounded-lg border p-3", selected ? "border-2 border-primary-600" : "border-line hover:border-primary-200")}
            >
              <div className="flex items-center gap-3">
                <Truck className="size-6 shrink-0 text-primary-600" strokeWidth={1.75} aria-hidden />
                <span className="min-w-0 flex-1 truncate text-sm font-semibold text-ink">{route.driver_name}</span>
                <button
                  type="button"
                  onClick={() => onSelect(route.id)}
                  aria-pressed={selected}
                  className={cn(
                    "h-7 shrink-0 rounded-md border px-2.5 text-xs font-medium",
                    selected ? "border-primary-600 bg-primary-600 text-white" : "border-primary-600 text-primary-700 hover:bg-primary-50",
                  )}
                >
                  {selected ? "Planning" : "Change route"}
                </button>
              </div>
              <p className="mt-2 pl-9 text-xs text-neutral-600">
                {route.stops_pending} of {route.stops_total} stops left
                {route.orders_at_risk > 0 && <span className="font-semibold text-danger-700"> - {route.orders_at_risk} at SLA risk</span>}
              </p>
              <p className="mt-1 flex items-center justify-between pl-9 text-xs text-neutral-500">
                <span className="flex items-center gap-1.5">
                  Hub <span className="w-6 border-t border-neutral-400" aria-hidden /> {formatClock(route.last_eta)}
                </span>
                <span>{km(route.total_distance_m)}</span>
              </p>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** Time between consecutive stops as one bar (Figma "Average Time Per Day"). */
function StopTimeBar({ stops }: { stops: EditorStop[] }) {
  // Read once per draft: the bar is keyed by the route, so a refreshed route remeasures.
  const [now] = useState(() => Date.now());
  const times = stops.map((stop) => (stop.eta ? new Date(stop.eta).getTime() : null));
  const legs = times.map((time, index) => {
    const previous = index === 0 ? now : times[index - 1];
    return time !== null && previous !== null ? Math.max(1, Math.round((time - previous) / 60_000)) : 0;
  });
  const total = legs.reduce((sum, minutes) => sum + minutes, 0);
  if (!total) return null;
  const shades = ["bg-primary-100", "bg-primary-200", "bg-primary-500", "bg-primary-600", "bg-primary-800"];
  return (
    <div>
      <div className="flex text-[11px] text-neutral-500">
        <span className="w-12 shrink-0">Now</span>
        {stops.map((stop, index) =>
          legs[index] ? (
            <span key={stop.id} className="min-w-0 truncate text-right" style={{ width: `${(legs[index] / total) * 100}%` }}>
              {legs[index] / total >= 0.12 ? `Stop ${index + 1}` : ""}
            </span>
          ) : null,
        )}
      </div>
      <div className="mt-1 flex h-7 gap-0.5 overflow-hidden rounded-md" role="img" aria-label={`About ${total} minutes to the last stop`}>
        {stops.map((stop, index) =>
          legs[index] ? (
            <span
              key={stop.id}
              className={cn("flex items-center justify-center text-[11px] font-medium", shades[index % shades.length], index % shades.length > 1 ? "text-white" : "text-primary-800")}
              style={{ width: `${(legs[index] / total) * 100}%` }}
              title={`${stop.name}: ${legs[index]} min`}
            >
              {legs[index] >= 8 ? `${legs[index]}m` : ""}
            </span>
          ) : null,
        )}
      </div>
    </div>
  );
}

function RouteWorkspace({
  routes,
  selectedId,
  onSelect,
  route,
}: {
  routes: RouteSummary[];
  selectedId: string | null;
  onSelect: (routeId: string) => void;
  route: RouteDetail | undefined;
}) {
  const optimize = useOptimizeRoute();
  const save = useSaveStopOrder();
  const pending = route?.stops.filter((stop) => stop.status === "PENDING") ?? [];
  const done = route?.stops.filter((stop) => stop.status !== "PENDING") ?? [];
  const [order, setOrder] = useState(() => pending.map((stop) => stop.id));
  const [suggestion, setSuggestion] = useState<OptimizeResult | null>(null);

  const stops: EditorStop[] = pending.map((stop) => ({
    id: stop.id,
    lat: stop.lat,
    lng: stop.lng,
    name: stop.recipient_name,
    address: stop.address,
    eta: stop.eta,
  }));
  const start: LatLng | null = route
    ? route.driver_lat !== null && route.driver_lng !== null
      ? [route.driver_lat, route.driver_lng]
      : [route.hub_lat, route.hub_lng]
    : null;
  const usesSuggestion = suggestion !== null && suggestion.suggested_stop_ids.join() === order.join();
  const map = start
    ? stopOrderMap({
        start,
        stops,
        order,
        currentGeometry: route?.geometry,
        draftGeometry: usesSuggestion ? suggestion?.suggested_geometry : null,
      })
    : { points: [], lines: [], changed: false };
  const changed = map.changed;

  return (
    <div className="grid grid-cols-1 gap-5 xl:h-[calc(100vh-7.5rem)] xl:grid-cols-[minmax(0,1fr)_400px] [&>*]:min-w-0">
      <section className="flex min-h-[640px] flex-col overflow-hidden rounded-lg border border-line bg-white">
        <header className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
          <h1 className="font-sans text-[17px] font-medium text-ink">Route planning</h1>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              disabled={!route || pending.length < 2}
              loading={optimize.isPending}
              onClick={() =>
                route &&
                optimize.mutate(route.id, {
                  onSuccess: (result) => {
                    setSuggestion(result);
                    setOrder(result.suggested_stop_ids);
                  },
                })
              }
            >
              <Sparkles className="mr-2 size-4" aria-hidden />
              Suggest best order
            </Button>
            <Button
              disabled={!route || !changed}
              loading={save.isPending}
              onClick={() => route && save.mutate({ routeId: route.id, stopIds: order })}
            >
              <Send className="mr-2 size-4" aria-hidden />
              Save and send to driver
            </Button>
          </div>
        </header>
        <div className="relative flex flex-1 flex-col gap-3 p-3 lg:block lg:p-0">
          <MapView
            points={map.points}
            lines={map.lines}
            showLabels
            fitPadding={{ topLeft: [370, 50], bottomRight: [50, 190] }}
            zoomPosition="topright"
            className="h-80 lg:absolute lg:inset-0 lg:h-full lg:rounded-none lg:border-0"
          />
          <div className="z-[500] flex max-h-96 flex-col lg:absolute lg:top-4 lg:bottom-40 lg:left-4 lg:max-h-none lg:w-80">
            <RouteList routes={routes} selectedId={selectedId} onSelect={onSelect} />
          </div>
          {route && (
            <div className="z-[500] grid gap-4 rounded-lg bg-white p-4 shadow-lg lg:absolute lg:right-4 lg:bottom-4 lg:left-[352px] lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-xs text-neutral-500">Driver</dt>
                  <dd className="font-medium text-ink">{route.driver_name}</dd>
                  <dd className="text-xs text-neutral-500">{formatPhone(route.driver_phone)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-neutral-500">Stops left</dt>
                  <dd className="font-medium text-ink">{pending.length}</dd>
                </div>
                <div>
                  <dt className="text-xs text-neutral-500">Remaining distance</dt>
                  <dd className="font-medium text-ink">{km(route.total_distance_m)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-neutral-500">Remaining driving</dt>
                  <dd className="font-medium text-ink">{duration(route.total_duration_s)}</dd>
                </div>
              </dl>
              <div className="flex min-w-0 flex-col justify-between gap-2">
                <p className="flex items-center justify-between text-sm">
                  <span className="font-medium text-ink">Time to each stop</span>
                  <span className="text-xs text-neutral-500">{route.eta_is_estimate ? "Estimate" : "Road network (OSRM)"}</span>
                </p>
                <StopTimeBar stops={stops} />
                {changed && <p className="text-xs text-neutral-500">Dashed red: current order. Blue: new order.</p>}
              </div>
            </div>
          )}
        </div>
      </section>

      <Panel
        title="Stops"
        action={route && <Badge tone="primary">{`${pending.length} stops left`}</Badge>}
        className="min-h-0"
        bodyClassName="flex min-h-0 flex-col gap-3 overflow-y-auto"
      >
        {!route && <EmptyState title="Choose a route">Pick a driver on the map to plan their stops.</EmptyState>}
        {suggestion && (usesSuggestion || !changed) && (
          <Alert tone={suggestion.changed ? "success" : "info"}>
            {suggestion.changed
              ? `Suggested order: about ${duration(suggestion.suggested_duration_s)} of driving instead of ${duration(suggestion.current_duration_s)} (${suggestion.method === "osrm" ? "road network" : "nearest stop first"}).`
              : "The current order is already the fastest one found."}
          </Alert>
        )}
        {route && pending.length === 0 && <EmptyState title="Every stop is done" />}
        {changed && (
          <Button size="sm" variant="ghost" className="self-start" onClick={() => setOrder(pending.map((stop) => stop.id))}>
            Reset to the current order
          </Button>
        )}
        {pending.length > 0 && <StopOrderList stops={stops} order={order} onChange={setOrder} />}
        {done.length > 0 && (
          <section className="border-t border-line pt-3">
            <h3 className="mb-2 font-sans text-sm text-neutral-600">Finished stops ({done.length})</h3>
            <ul className="flex flex-col gap-2 text-sm">
              {done.map((stop) => (
                <li key={stop.id} className="flex items-center justify-between gap-3 text-neutral-600">
                  <span className="truncate">{stop.recipient_name}</span>
                  <span className="flex shrink-0 gap-1">
                    {stop.orders.map((item) => (
                      <OrderStatusBadge key={item.id} status={item.status} />
                    ))}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}
      </Panel>
    </div>
  );
}

export function RoutePlanningPage() {
  const [params, setParams] = useSearchParams();
  const routes = useRoutes();
  const selectedId = params.get("route") ?? routes.data?.find((route) => route.stops_pending > 0)?.id ?? null;
  const route = useRouteDetail(selectedId);

  if (routes.isPending) return <Loading />;
  if (routes.isError) return <Alert tone="danger">{errorMessage(routes.error)}</Alert>;
  if (routes.data.length === 0) {
    return <EmptyState title="No route today yet">Routes appear when drivers accept orders.</EmptyState>;
  }
  if (route.isError) return <Alert tone="danger">{errorMessage(route.error)}</Alert>;

  const pendingKey = route.data?.stops.filter((stop) => stop.status === "PENDING").map((stop) => stop.id).join() ?? "";
  return (
    // Keyed by the route and its pending stops so a refreshed route starts a fresh draft.
    <RouteWorkspace
      key={`${route.data?.id ?? "none"}-${pendingKey}`}
      routes={routes.data}
      selectedId={selectedId}
      onSelect={(routeId) => setParams({ route: routeId }, { replace: true })}
      route={route.data}
    />
  );
}
