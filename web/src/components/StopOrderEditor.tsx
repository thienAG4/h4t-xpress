// StopOrderEditor - reorder pending stops with Up/Down and compare the routes on a map
// (H-02 route planning, H-08 reroute). The current route is red and dashed, the new one blue.

import { MapView, type MapLine, type MapPoint } from "@/components/MapView";
import { Button } from "@/components/ui";
import { formatClock } from "@/lib/format";
import { routeLine, type LatLng } from "@/lib/polyline";

export type EditorStop = {
  id: string;
  lat: number;
  lng: number;
  name: string;
  address: string;
  eta: string | null;
};

type Props = {
  start: LatLng;
  stops: EditorStop[]; // current order
  order: string[]; // draft order (stop ids)
  onChange: (order: string[]) => void;
  currentGeometry?: string | null;
  draftGeometry?: string | null; // road geometry of the draft when it came from the optimiser
  className?: string;
};

export function StopOrderEditor({ start, stops, order, onChange, currentGeometry, draftGeometry, className }: Props) {
  const byId = new Map(stops.map((stop) => [stop.id, stop]));
  const draft = order.map((id) => byId.get(id)).filter((stop): stop is EditorStop => Boolean(stop));
  const changed = order.some((id, index) => id !== stops[index]?.id);

  const move = (index: number, offset: -1 | 1) => {
    const next = [...order];
    [next[index], next[index + offset]] = [next[index + offset], next[index]];
    onChange(next);
  };

  const points: MapPoint[] = [
    { id: "start", lat: start[0], lng: start[1], label: "Driver", kind: "driver" },
    ...draft.map((stop, index) => ({
      id: stop.id,
      lat: stop.lat,
      lng: stop.lng,
      label: `${index + 1}. ${stop.name}`,
      tag: String(index + 1),
      kind: "stop" as const,
    })),
  ];
  const currentLine = routeLine(currentGeometry, [start, ...stops.map((stop): LatLng => [stop.lat, stop.lng])]);
  const draftLine = draftGeometry
    ? routeLine(draftGeometry, [])
    : [start, ...draft.map((stop): LatLng => [stop.lat, stop.lng])];
  const lines: MapLine[] = changed
    ? [
        { id: "current", positions: currentLine, color: "#f8183e", dashed: true },
        { id: "draft", positions: draftLine },
      ]
    : [{ id: "current", positions: currentLine }];

  return (
    <div className={className}>
      <MapView points={points} lines={lines} showLabels className="h-72" />
      {changed && <p className="mt-2 text-xs text-neutral-600">Dashed red: current order. Blue: new order.</p>}
      <ol className="mt-3 flex flex-col gap-2">
        {draft.map((stop, index) => (
          <li key={stop.id} className="flex items-center gap-3 rounded-input border border-line bg-white px-3 py-2 text-sm">
            <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary-600 text-xs font-bold text-white">
              {index + 1}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate font-semibold">{stop.name}</span>
              <span className="block truncate text-xs text-neutral-600">
                {stop.address} - ETA {formatClock(stop.eta)}
              </span>
            </span>
            <span className="flex gap-1">
              <Button size="sm" variant="secondary" disabled={index === 0} onClick={() => move(index, -1)}>
                Up
              </Button>
              <Button size="sm" variant="secondary" disabled={index === draft.length - 1} onClick={() => move(index, 1)}>
                Down
              </Button>
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
