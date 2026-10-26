// RoutePage - D-07: today's route on a map, parcels to collect, then stops in delivery order

import { useState } from "react";
import { Link } from "react-router";
import { MapLegend, MapView, type MapLine, type MapPoint } from "@/components/MapView";
import { ScreenTitle } from "@/components/ScreenTitle";
import { Alert, Badge, Button, Card, Dialog, EmptyState, Loading, SelectField } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatClock, formatMoney } from "@/lib/format";
import { routeLine, type LatLng } from "@/lib/polyline";
import type { DriverOrder, DriverRoute } from "@/types";
import { ScanDialog } from "../components/ScanDialog";
import { StopCard } from "../components/StopCard";
import { useReleaseOrder, useRoute, useStartRoute } from "../hooks";

const RELEASE_REASONS = [
  { value: "Vehicle problem before pickup", label: "Vehicle problem before pickup" },
  { value: "Cannot reach the hub in time", label: "Cannot reach the hub in time" },
  { value: "Parcel too large for my vehicle", label: "Parcel too large for my vehicle" },
];

function mapData(route: DriverRoute): { points: MapPoint[]; lines: MapLine[] } {
  const points: MapPoint[] = [
    { id: "hub", lat: route.hub_lat, lng: route.hub_lng, label: route.hub_name, kind: "hub" },
    ...route.stops.map((stop, index) => ({
      id: stop.id,
      lat: stop.lat,
      lng: stop.lng,
      label: `${index + 1}. ${stop.recipient_name}`,
      tag: String(index + 1),
      kind: "stop" as const,
    })),
  ];
  const start: LatLng =
    route.driver_lat !== null && route.driver_lng !== null
      ? [route.driver_lat, route.driver_lng]
      : [route.hub_lat, route.hub_lng];
  if (route.driver_lat !== null && route.driver_lng !== null) {
    points.push({ id: "me", lat: route.driver_lat, lng: route.driver_lng, label: "You are here", kind: "driver" });
  }
  // Road geometry from OSRM when available, straight segments in stop order otherwise.
  const straight: LatLng[] = [start, ...route.stops.map((stop): LatLng => [stop.lat, stop.lng])];
  const lines: MapLine[] = route.stops.length
    ? [{ id: "route", positions: routeLine(route.geometry, straight) }]
    : [];
  return { points, lines };
}

export function RoutePage() {
  const route = useRoute();
  const start = useStartRoute();
  const release = useReleaseOrder();
  const [scanning, setScanning] = useState<DriverOrder | null>(null);
  const [releasing, setReleasing] = useState<DriverOrder | null>(null);
  const [releaseReason, setReleaseReason] = useState(RELEASE_REASONS[0].value);

  if (route.isPending) return <Loading />;
  if (route.isError) return <Alert tone="danger">{errorMessage(route.error)}</Alert>;

  const data = route.data;
  const { points, lines } = mapData(data);
  const empty = !data.to_pick_up.length && !data.stops.length && !data.ready_to_start;

  return (
    <div className="flex flex-col gap-4">
      <ScreenTitle title="Today's route" />
      <MapView points={points} lines={lines} showLabels className="h-56" />
      <MapLegend kinds={["hub", "driver", "stop"]} />

      {empty && (
        <EmptyState title="No orders on your route">
          Stay online on the{" "}
          <Link to="/driver" className="font-semibold text-primary-600">
            Home
          </Link>{" "}
          tab. New offers pop up here.
        </EmptyState>
      )}

      {data.to_pick_up.length > 0 && (
        <Card title={`To pick up (${data.to_pick_up.length})`}>
          <ul className="flex flex-col divide-y divide-line">
            {data.to_pick_up.map((order) => (
              <li key={order.id} className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                <div className="min-w-0">
                  <p className="font-semibold">{order.waybill_code}</p>
                  <p className="truncate text-xs text-neutral-600">
                    {order.handover_from ? `Collect from ${order.handover_from}` : `At ${data.hub_name}`}
                  </p>
                  {order.priority === "EXPRESS" && <Badge tone="danger">Express</Badge>}
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1">
                  <Button size="sm" onClick={() => setScanning(order)}>
                    Scan
                  </Button>
                  {!order.handover_from && (
                    <button
                      type="button"
                      onClick={() => setReleasing(order)}
                      className="text-xs font-semibold text-neutral-500 hover:text-danger-700"
                    >
                      Give back
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {data.ready_to_start > 0 && (
        <Button size="lg" block loading={start.isPending} onClick={() => start.mutate()}>
          Start delivery ({data.ready_to_start} scanned)
        </Button>
      )}

      {data.stops.length > 0 && (
        <section className="flex flex-col gap-3">
          <h2 className="text-base font-semibold">Stops ({data.stops.length})</h2>
          {data.stops.map((stop, index) => (
            <StopCard key={stop.id} stop={stop} position={index + 1} />
          ))}
          <p className="text-xs text-neutral-500">
            Cash to collect today:{" "}
            {formatMoney(
              data.stops.flatMap((stop) => stop.orders).reduce((sum, order) => sum + Number(order.cod_amount), 0),
            )}
            {data.stops[0]?.eta && ` - first stop around ${formatClock(data.stops[0].eta)}`}
          </p>
        </section>
      )}

      <ScanDialog order={scanning} onClose={() => setScanning(null)} />
      <Dialog
        open={Boolean(releasing)}
        title={`Give back ${releasing?.waybill_code ?? ""}?`}
        onClose={() => setReleasing(null)}
        actions={
          <>
            <Button variant="secondary" onClick={() => setReleasing(null)}>
              Keep it
            </Button>
            <Button
              variant="danger"
              loading={release.isPending}
              onClick={() =>
                releasing &&
                release.mutate(
                  { orderId: releasing.id, reason: releaseReason },
                  { onSettled: () => setReleasing(null) },
                )
              }
            >
              Give back
            </Button>
          </>
        }
      >
        <p className="mb-3">Only possible before pickup. Dispatch offers the order to another driver.</p>
        <SelectField
          label="Reason"
          options={RELEASE_REASONS}
          value={releaseReason}
          onChange={(event) => setReleaseReason(event.target.value)}
        />
      </Dialog>
    </div>
  );
}
