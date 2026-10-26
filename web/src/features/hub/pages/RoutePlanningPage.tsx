// RoutePlanningPage - H-02 (Figma "Lên kế hoạch tuyến đường"): today's routes on the left,
// the selected route on a road map with its stops, an OSRM suggestion and saving a new order.

import { useState } from "react";
import { useSearchParams } from "react-router";
import { PageHeader } from "@/components/PageHeader";
import { OrderStatusBadge } from "@/components/StatusBadge";
import { StopOrderEditor, type EditorStop } from "@/components/StopOrderEditor";
import { Alert, Badge, Button, Card, EmptyState, Loading } from "@/components/ui";
import { cn } from "@/lib/cn";
import { errorMessage } from "@/lib/errors";
import { formatClock, formatPhone } from "@/lib/format";
import type { LatLng } from "@/lib/polyline";
import type { OptimizeResult, RouteDetail } from "@/types";
import { useOptimizeRoute, useRouteDetail, useRoutes, useSaveStopOrder } from "../hooks";

function km(meters: number | null): string {
  return meters === null ? "-" : `${(meters / 1000).toFixed(1)} km`;
}

function duration(seconds: number | null): string {
  if (seconds === null) return "-";
  const minutes = Math.round(seconds / 60);
  return minutes >= 60 ? `${Math.floor(minutes / 60)} h ${minutes % 60} min` : `${minutes} min`;
}

function RoutePlanner({ route }: { route: RouteDetail }) {
  const optimize = useOptimizeRoute();
  const save = useSaveStopOrder();
  const pending = route.stops.filter((stop) => stop.status === "PENDING");
  const done = route.stops.filter((stop) => stop.status !== "PENDING");
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
  const start: LatLng =
    route.driver_lat !== null && route.driver_lng !== null ? [route.driver_lat, route.driver_lng] : [route.hub_lat, route.hub_lng];
  const changed = order.some((id, index) => id !== pending[index]?.id);
  const usesSuggestion = suggestion !== null && suggestion.suggested_stop_ids.join() === order.join();

  return (
    <div className="flex flex-col gap-4">
      <Card
        title={route.driver_name}
        actions={<span className="text-sm text-neutral-600">{formatPhone(route.driver_phone)}</span>}
      >
        <dl className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
          <div>
            <dt className="text-xs text-neutral-500">Stops left</dt>
            <dd className="font-semibold">{pending.length}</dd>
          </div>
          <div>
            <dt className="text-xs text-neutral-500">Remaining distance</dt>
            <dd className="font-semibold">{km(route.total_distance_m)}</dd>
          </div>
          <div>
            <dt className="text-xs text-neutral-500">Remaining driving</dt>
            <dd className="font-semibold">{duration(route.total_duration_s)}</dd>
          </div>
          <div>
            <dt className="text-xs text-neutral-500">ETA source</dt>
            <dd className="font-semibold">{route.eta_is_estimate ? "Estimate" : "Road network (OSRM)"}</dd>
          </div>
        </dl>
      </Card>

      {pending.length === 0 ? (
        <EmptyState title="Every stop is done" />
      ) : (
        <Card title="Stop order">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant="secondary"
              disabled={pending.length < 2}
              loading={optimize.isPending}
              onClick={() =>
                optimize.mutate(route.id, {
                  onSuccess: (result) => {
                    setSuggestion(result);
                    setOrder(result.suggested_stop_ids);
                  },
                })
              }
            >
              Suggest best order
            </Button>
            {changed && (
              <Button size="sm" variant="ghost" onClick={() => setOrder(pending.map((stop) => stop.id))}>
                Reset
              </Button>
            )}
            <Button
              size="sm"
              disabled={!changed}
              loading={save.isPending}
              onClick={() => save.mutate({ routeId: route.id, stopIds: order })}
            >
              Save and send to driver
            </Button>
          </div>
          {suggestion && (usesSuggestion || !changed) && (
            <Alert tone={suggestion.changed ? "success" : "info"} className="mb-3">
              {suggestion.changed
                ? `Suggested order: about ${duration(suggestion.suggested_duration_s)} of driving instead of ${duration(suggestion.current_duration_s)} (${suggestion.method === "osrm" ? "road network" : "nearest stop first"}).`
                : "The current order is already the fastest one found."}
            </Alert>
          )}
          <StopOrderEditor
            start={start}
            stops={stops}
            order={order}
            onChange={setOrder}
            currentGeometry={route.geometry}
            draftGeometry={usesSuggestion ? suggestion?.suggested_geometry : null}
          />
        </Card>
      )}

      {done.length > 0 && (
        <Card title={`Finished stops (${done.length})`}>
          <ul className="flex flex-col gap-2 text-sm">
            {done.map((stop) => (
              <li key={stop.id} className="flex items-center justify-between gap-3 text-neutral-600">
                <span className="truncate">
                  {stop.recipient_name} - {stop.address}
                </span>
                <span className="flex shrink-0 gap-1">
                  {stop.orders.map((order) => (
                    <OrderStatusBadge key={order.id} status={order.status} />
                  ))}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

export function RoutePlanningPage() {
  const [params, setParams] = useSearchParams();
  const routes = useRoutes();
  const selectedId = params.get("route") ?? routes.data?.find((route) => route.stops_pending > 0)?.id ?? null;
  const route = useRouteDetail(selectedId);

  return (
    <>
      <PageHeader
        title="Route planning"
        description="Today's routes per driver. Reorder pending stops or let the road network suggest the fastest order."
      />
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[320px_1fr] [&>*]:min-w-0">
        <section className="flex flex-col gap-3">
          {routes.isPending && <Loading />}
          {routes.isError && <Alert tone="danger">{errorMessage(routes.error)}</Alert>}
          {routes.data?.length === 0 && <EmptyState title="No route today yet">Routes appear when drivers accept orders.</EmptyState>}
          {routes.data?.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setParams({ route: item.id }, { replace: true })}
              className={cn(
                "rounded-card border bg-white p-4 text-left transition-colors",
                item.id === selectedId ? "border-primary-600 ring-1 ring-primary-600" : "border-line hover:border-primary-200",
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold">{item.driver_name}</span>
                <Badge tone={item.status === "IN_PROGRESS" ? "primary" : item.status === "COMPLETED" ? "success" : "neutral"}>
                  {item.status === "IN_PROGRESS" ? "On the road" : item.status === "COMPLETED" ? "Done" : "Planned"}
                </Badge>
              </div>
              <p className="mt-1 text-xs text-neutral-600">
                {item.stops_pending} of {item.stops_total} stops left - {item.orders_active} active order
                {item.orders_active === 1 ? "" : "s"}
              </p>
              <p className="mt-1 text-xs text-neutral-600">
                Next {formatClock(item.next_eta)} - last {formatClock(item.last_eta)}
                {item.total_distance_m !== null ? ` - ${km(item.total_distance_m)}` : ""}
              </p>
              {item.orders_at_risk > 0 && (
                <p className="mt-1 text-xs font-semibold text-danger-700">{item.orders_at_risk} at SLA risk</p>
              )}
            </button>
          ))}
        </section>
        <section>
          {!selectedId && routes.data && routes.data.length > 0 && <EmptyState title="Choose a route" />}
          {route.isPending && selectedId && <Loading />}
          {route.isError && <Alert tone="danger">{errorMessage(route.error)}</Alert>}
          {/* Keyed by the stop list so a refreshed route starts a fresh draft. */}
          {route.data && (
            <RoutePlanner
              key={`${route.data.id}-${route.data.stops.filter((s) => s.status === "PENDING").map((s) => s.id).join()}`}
              route={route.data}
            />
          )}
        </section>
      </div>
    </>
  );
}
