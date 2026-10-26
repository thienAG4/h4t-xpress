// ReroutePanel - H-08: a new order for the reporting driver's remaining stops (UC-03).
// The road network can suggest the fastest order; the hub can still adjust it by hand.

import { useState } from "react";
import { StopOrderEditor, type EditorStop } from "@/components/StopOrderEditor";
import { Alert, Button, EmptyState, Loading, TextAreaField } from "@/components/ui";
import { useDriverRoute, useOptimizeRoute } from "@/features/hub/hooks";
import { errorMessage } from "@/lib/errors";
import type { LatLng } from "@/lib/polyline";
import type { DriverRoute, OptimizeResult } from "@/types";

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

function RerouteEditor({ route, submitting, error, onSubmit }: { route: DriverRoute } & Omit<Props, "driverId">) {
  const optimize = useOptimizeRoute();
  const [order, setOrder] = useState(() => route.stops.map((stop) => stop.id));
  const [suggestion, setSuggestion] = useState<OptimizeResult | null>(null);
  const [note, setNote] = useState("");

  const stops: EditorStop[] = route.stops.map((stop) => ({
    id: stop.id,
    lat: stop.lat,
    lng: stop.lng,
    name: stop.recipient_name,
    address: stop.address,
    eta: stop.eta,
  }));
  const start: LatLng =
    route.driver_lat !== null && route.driver_lng !== null ? [route.driver_lat, route.driver_lng] : [route.hub_lat, route.hub_lng];
  const changed = order.some((id, index) => id !== route.stops[index].id);
  const usesSuggestion = suggestion !== null && suggestion.suggested_stop_ids.join() === order.join();

  return (
    <div className="flex flex-col gap-3">
      {route.route_id && (
        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="secondary"
            loading={optimize.isPending}
            onClick={() =>
              optimize.mutate(route.route_id ?? "", {
                onSuccess: (result) => {
                  setSuggestion(result);
                  setOrder(result.suggested_stop_ids);
                },
              })
            }
          >
            Suggest best order
          </Button>
          {suggestion && (
            <span className="text-xs text-neutral-600">
              {suggestion.changed
                ? `Saves about ${Math.max(1, Math.round(((suggestion.current_duration_s ?? 0) - (suggestion.suggested_duration_s ?? 0)) / 60))} min of driving.`
                : "The current order is already the fastest."}
            </span>
          )}
        </div>
      )}
      <StopOrderEditor
        start={start}
        stops={stops}
        order={order}
        onChange={setOrder}
        currentGeometry={route.geometry}
        draftGeometry={usesSuggestion ? suggestion?.suggested_geometry : null}
      />
      <TextAreaField label="Note for the driver (optional)" rows={2} value={note} onChange={(event) => setNote(event.target.value)} />
      {Boolean(error) && <Alert tone="danger">{errorMessage(error)}</Alert>}
      <Button disabled={!changed} loading={submitting} onClick={() => onSubmit(order, note.trim() || null)}>
        {changed ? "Send the new route to the driver" : "Move a stop to change the route"}
      </Button>
    </div>
  );
}
