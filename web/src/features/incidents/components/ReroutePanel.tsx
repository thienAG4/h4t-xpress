// ReroutePanel - H-08: give the driver's remaining stops a new order and send it (UC-03).
// Stops move with "Up" / "Down" buttons; the map redraws the route in the new order.

import { useState } from "react";
import { MapView, type MapPoint } from "@/components/MapView";
import { Alert, Button, EmptyState, Loading, TextAreaField } from "@/components/ui";
import { useDriverRoute } from "@/features/hub/hooks";
import { errorMessage } from "@/lib/errors";
import { formatClock } from "@/lib/format";
import type { DriverRoute, RouteStop } from "@/types";

type Props = {
  driverId: string;
  submitting: boolean;
  error: unknown;
  onSubmit: (stopIds: string[], note: string | null) => void;
};

export function ReroutePanel({ driverId, submitting, error, onSubmit }: Props) {
  const route = useDriverRoute(driverId);
  if (route.isPending) return <Loading label="Loading the driver's route..." />;
  if (route.isError) return <Alert tone="danger">{errorMessage(route.error)}</Alert>;
  if (route.data.stops.length < 2) {
    return <EmptyState title="Nothing to reorder">The driver has fewer than two stops left.</EmptyState>;
  }
  // Keyed by the route content so a refreshed route starts a fresh draft.
  return (
    <RerouteEditor
      key={route.data.stops.map((stop) => stop.id).join()}
      route={route.data}
      submitting={submitting}
      error={error}
      onSubmit={onSubmit}
    />
  );
}

function RerouteEditor({
  route,
  submitting,
  error,
  onSubmit,
}: { route: DriverRoute } & Omit<Props, "driverId">) {
  const [stops, setStops] = useState<RouteStop[]>(route.stops);
  const [note, setNote] = useState("");

  const move = (index: number, offset: -1 | 1) =>
    setStops((current) => {
      const next = [...current];
      [next[index], next[index + offset]] = [next[index + offset], next[index]];
      return next;
    });

  const start: [number, number] =
    route.driver_lat !== null && route.driver_lng !== null ? [route.driver_lat, route.driver_lng] : [route.hub_lat, route.hub_lng];
  const points: MapPoint[] = [
    { id: "driver", lat: start[0], lng: start[1], label: "Driver", kind: "driver" },
    ...stops.map((stop, index) => ({
      id: stop.id,
      lat: stop.lat,
      lng: stop.lng,
      label: `${index + 1}. ${stop.recipient_name}`,
      tag: String(index + 1),
      kind: "stop" as const,
    })),
  ];
  const before = [start, ...route.stops.map((stop) => [stop.lat, stop.lng] as [number, number])];
  const after = [start, ...stops.map((stop) => [stop.lat, stop.lng] as [number, number])];
  const changed = stops.some((stop, index) => stop.id !== route.stops[index].id);

  return (
    <div className="flex flex-col gap-3">
      <MapView
        points={points}
        showLabels
        lines={[
          { id: "before", positions: before, color: "#f8183e", dashed: true },
          { id: "after", positions: after, color: "#1070f8" },
        ]}
        className="h-64"
      />
      <p className="text-xs text-neutral-600">Dashed red: current order. Blue: new order.</p>
      <ol className="flex flex-col gap-2">
        {stops.map((stop, index) => (
          <li key={stop.id} className="flex items-center gap-3 rounded-input border border-line bg-white px-3 py-2 text-sm">
            <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary-600 text-xs font-bold text-white">
              {index + 1}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate font-semibold">{stop.recipient_name}</span>
              <span className="block truncate text-xs text-neutral-600">
                {stop.address} - ETA {formatClock(stop.eta)}
              </span>
            </span>
            <span className="flex gap-1">
              <Button size="sm" variant="secondary" disabled={index === 0} onClick={() => move(index, -1)}>
                Up
              </Button>
              <Button size="sm" variant="secondary" disabled={index === stops.length - 1} onClick={() => move(index, 1)}>
                Down
              </Button>
            </span>
          </li>
        ))}
      </ol>
      <TextAreaField label="Note for the driver (optional)" rows={2} value={note} onChange={(event) => setNote(event.target.value)} />
      {Boolean(error) && <Alert tone="danger">{errorMessage(error)}</Alert>}
      <Button
        disabled={!changed}
        loading={submitting}
        onClick={() => onSubmit(stops.map((stop) => stop.id), note.trim() || null)}
      >
        {changed ? "Send the new route to the driver" : "Move a stop to change the route"}
      </Button>
    </div>
  );
}
