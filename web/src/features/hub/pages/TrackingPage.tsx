// TrackingPage - H-03 (Figma "Theo dõi giao hàng"): drivers on the left, the live map in the
// middle with a summary of the tracked route, the selected order's status and actions on the right.

import { Clock3, MapPin, Milestone, Navigation, Package, Search } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { MapLegend, MapView, type MapLine, type MapPoint } from "@/components/MapView";
import { OrderStatusBadge } from "@/components/StatusBadge";
import { Alert, EmptyState, Loading, Panel } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatClock } from "@/lib/format";
import { routeLine, type LatLng } from "@/lib/polyline";
import type { DriverRoute, HubDriverRow, HubOrderDetail } from "@/types";
import { DriversPanel } from "../components/DriversPanel";
import { OrderPanel } from "../components/OrderPanel";
import { useDriverRoute, useHubDrivers, useHubOrder, useHubOrders } from "../hooks";

function buildMap(
  drivers: HubDriverRow[],
  selectedDriver: string | null,
  route: DriverRoute | undefined,
  order: HubOrderDetail | undefined,
): { points: MapPoint[]; lines: MapLine[] } {
  const points: MapPoint[] = [];
  const lines: MapLine[] = [];
  const hub = order ? { lat: order.hub_lat, lng: order.hub_lng } : route ? { lat: route.hub_lat, lng: route.hub_lng } : null;
  if (hub) points.push({ id: "hub", ...hub, label: route?.hub_name || "Hub", kind: "hub" });

  for (const driver of drivers) {
    const visible = driver.availability === "ONLINE" || driver.active_orders > 0;
    if (driver.lat === null || driver.lng === null || !visible) continue;
    const highlighted = driver.id === selectedDriver || driver.id === order?.driver_id;
    points.push({
      id: `driver-${driver.id}`,
      lat: driver.lat,
      lng: driver.lng,
      label: `${driver.name} - ${driver.active_orders} orders`,
      kind: highlighted ? "selected" : "driver",
    });
  }
  if (route) {
    route.stops.forEach((stop, index) =>
      points.push({
        id: `stop-${stop.id}`,
        lat: stop.lat,
        lng: stop.lng,
        label: `${index + 1}. ${stop.recipient_name} - ETA ${formatClock(stop.eta)}`,
        tag: String(index + 1),
        kind: "stop",
      }),
    );
    const start: LatLng =
      route.driver_lat !== null && route.driver_lng !== null ? [route.driver_lat, route.driver_lng] : [route.hub_lat, route.hub_lng];
    if (route.stops.length) {
      const straight: LatLng[] = [start, ...route.stops.map((stop): LatLng => [stop.lat, stop.lng])];
      lines.push({ id: "route", positions: routeLine(route.geometry, straight) });
    }
  }
  if (order && !route?.stops.some((stop) => stop.orders.some((item) => item.id === order.id))) {
    points.push({ id: "destination", lat: order.delivery_lat, lng: order.delivery_lng, label: order.recipient_name, kind: "stop" });
  }
  return { points, lines };
}

function OrderPicker() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const orders = useHubOrders({ page: 1, page_size: 12, q: search.trim() || undefined });
  return (
    <Panel title="Find an order" bodyClassName="flex flex-col gap-3">
      <label className="relative">
        <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-neutral-400" aria-hidden />
        <input
          type="search"
          aria-label="Find an order"
          placeholder="Waybill, name or phone"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="h-10 w-full rounded-lg border border-line pr-3 pl-9 text-sm placeholder:text-placeholder focus:border-primary-500 focus:outline-none"
        />
      </label>
      <ul className="flex flex-col gap-2">
        {orders.isPending && <Loading />}
        {orders.data?.items.map((order) => (
          <li key={order.id}>
            <button
              type="button"
              onClick={() => navigate(`/hub/tracking/${order.id}`)}
              className="flex w-full items-center justify-between gap-2 rounded-lg border border-line px-3 py-2.5 text-left text-sm hover:border-primary-200 hover:bg-primary-50/30"
            >
              <span className="flex items-center gap-3">
                <Package className="size-4 text-primary-600" aria-hidden />
                <span>
                  <span className="font-medium text-ink">{order.waybill_code}</span>
                  <span className={order.at_risk ? "block text-xs text-danger-700" : "block text-xs text-neutral-500"}>
                    {order.at_risk ? "SLA risk - " : ""}promised {formatClock(order.promised_at)}
                  </span>
                </span>
              </span>
              <OrderStatusBadge status={order.status} />
            </button>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

/** One figure of the white summary card at the bottom of the Figma map. */
function MapFact({ icon: Icon, value, label }: { icon: typeof Clock3; value: ReactNode; label: string }) {
  return (
    <div className="flex items-start gap-2.5">
      <Icon className="mt-0.5 size-5 shrink-0 text-primary-700" strokeWidth={1.75} aria-hidden />
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-ink">{value}</p>
        <p className="text-xs text-neutral-500">{label}</p>
      </div>
    </div>
  );
}

export function TrackingPage() {
  const { orderId } = useParams();
  const [params, setParams] = useSearchParams();
  const order = useHubOrder(orderId);
  const drivers = useHubDrivers();
  // Following an order follows its driver unless another driver was picked explicitly.
  const selectedDriver = params.get("driver") ?? order.data?.driver_id ?? null;
  const route = useDriverRoute(selectedDriver);
  const { points, lines } = buildMap(drivers.data ?? [], selectedDriver, route.data, order.data);

  const selectDriver = (driverId: string | null) => {
    const next = new URLSearchParams(params);
    if (driverId) next.set("driver", driverId);
    else next.delete("driver");
    setParams(next, { replace: true });
  };

  const nextStop = route.data?.stops[0];
  const lastStop = route.data?.stops[route.data.stops.length - 1];

  return (
    <div className="grid grid-cols-1 gap-5 xl:h-[calc(100vh-7.5rem)] xl:grid-cols-[320px_minmax(0,1fr)_380px] [&>*]:min-w-0">
      <DriversPanel selectedId={selectedDriver} onSelect={selectDriver} route={route.data} />

      <section className="flex min-h-[460px] flex-col overflow-hidden rounded-lg border border-line bg-white">
        <header className="flex items-center justify-between gap-3 px-5 py-3">
          <div>
            <p className="text-sm text-neutral-500">{order.data ? "Shipment ID" : "Delivery tracking"}</p>
            <h1 className="font-sans text-2xl font-medium text-ink">{order.data ? `#${order.data.waybill_code}` : "Live map"}</h1>
          </div>
          {orderId && (
            <Link
              to="/hub/tracking"
              className="inline-flex h-10 items-center rounded-md bg-primary-600 px-8 text-sm font-medium text-white hover:bg-primary-700"
            >
              Back
            </Link>
          )}
        </header>
        <div className="relative flex-1">
          <MapView
            points={points}
            lines={lines}
            showLabels
            fitPadding={route.data ? { topLeft: [40, 40], bottomRight: [40, 130] } : undefined}
            className="h-full min-h-[380px] rounded-none border-0"
          />
          {route.data && (
            <div className="absolute right-4 bottom-4 left-4 z-[500] grid grid-cols-2 gap-4 rounded-lg bg-white p-4 shadow-lg lg:grid-cols-4">
              <MapFact icon={Navigation} value={nextStop ? nextStop.recipient_name : route.data.hub_name} label="Next stop" />
              <MapFact icon={Milestone} value={`${route.data.stops.length} stops`} label="Left on the route" />
              <MapFact icon={Clock3} value={formatClock(nextStop?.eta)} label="Next arrival" />
              <MapFact icon={MapPin} value={formatClock(lastStop?.eta)} label="Last stop" />
            </div>
          )}
        </div>
        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-5 py-3">
          <MapLegend kinds={["hub", "driver", "stop"]} />
          {route.data && (
            <p className="text-xs text-neutral-600">
              {route.data.stops.length} stops left - {route.data.to_pick_up.length} to pick up
            </p>
          )}
        </footer>
      </section>

      <div className="flex min-h-0 flex-col gap-5 overflow-y-auto">
        {!orderId && <OrderPicker />}
        {orderId && order.isPending && <Loading />}
        {orderId && order.isError && <Alert tone="danger">{errorMessage(order.error)}</Alert>}
        {order.data && <OrderPanel order={order.data} />}
        {!orderId && !selectedDriver && (
          <EmptyState title="Pick an order or a driver">Their route and timeline appear here.</EmptyState>
        )}
      </div>
    </div>
  );
}
