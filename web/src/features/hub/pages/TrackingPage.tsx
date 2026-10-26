// TrackingPage - H-03 (Figma "Theo dõi giao hàng"): drivers on the left, live map in the
// middle, the selected order's status and actions on the right.

import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { MapLegend, MapView, type MapLine, type MapPoint } from "@/components/MapView";
import { OrderStatusBadge } from "@/components/StatusBadge";
import { Alert, Card, EmptyState, Loading, TextField } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatClock, formatDateTime } from "@/lib/format";
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
    <Card title="Find an order">
      <TextField compact placeholder="Waybill, name or phone" value={search} onChange={(event) => setSearch(event.target.value)} />
      <ul className="mt-3 flex flex-col gap-2">
        {orders.isPending && <Loading />}
        {orders.data?.items.map((order) => (
          <li key={order.id}>
            <button
              type="button"
              onClick={() => navigate(`/hub/tracking/${order.id}`)}
              className="flex w-full items-center justify-between gap-2 rounded-input border border-line px-3 py-2 text-left text-sm hover:border-primary-200"
            >
              <span>
                <span className="font-semibold">{order.waybill_code}</span>
                <span className={order.at_risk ? "block text-xs text-danger-700" : "block text-xs text-neutral-600"}>
                  {order.at_risk ? "SLA risk - " : ""}promised {formatClock(order.promised_at)}
                </span>
              </span>
              <OrderStatusBadge status={order.status} />
            </button>
          </li>
        ))}
      </ul>
    </Card>
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

  return (
    <div className="grid grid-cols-1 gap-4 xl:h-[calc(100vh-8rem)] xl:grid-cols-[300px_1fr_380px] [&>*]:min-w-0">
      <DriversPanel selectedId={selectedDriver} onSelect={selectDriver} />

      <section className="flex min-h-[420px] flex-col rounded-card border border-line bg-white">
        <header className="flex items-center justify-between gap-3 border-b border-line p-4">
          <div>
            <p className="text-xs text-neutral-500">Shipment</p>
            <h1 className="text-xl font-bold">{order.data ? `#${order.data.waybill_code}` : "Live map"}</h1>
          </div>
          {orderId && (
            <Link to="/hub/tracking" className="inline-flex h-10 items-center rounded-button bg-primary-600 px-4 text-sm font-semibold text-white">
              Back
            </Link>
          )}
        </header>
        <div className="relative flex-1 p-3">
          <MapView points={points} lines={lines} showLabels className="h-full min-h-[360px]" />
        </div>
        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-4 py-3">
          <MapLegend kinds={["hub", "driver", "stop"]} />
          {route.data && (
            <p className="text-xs text-neutral-600">
              {route.data.stops.length} stops left - {route.data.to_pick_up.length} to pick up
            </p>
          )}
        </footer>
      </section>

      <div className="flex min-h-0 flex-col gap-4 overflow-y-auto">
        {!orderId && <OrderPicker />}
        {orderId && order.isPending && <Loading />}
        {orderId && order.isError && <Alert tone="danger">{errorMessage(order.error)}</Alert>}
        {order.data && <OrderPanel order={order.data} />}
        {!orderId && !selectedDriver && (
          <EmptyState title="Pick an order or a driver">Their route and timeline appear here.</EmptyState>
        )}
        {order.data && (
          <p className="text-xs text-neutral-500">Created {formatDateTime(order.data.created_at)}</p>
        )}
      </div>
    </div>
  );
}
