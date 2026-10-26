// Stop order helpers - points and lines comparing the current route with a draft order
// (shared by the stop order editor and the route planning map)

import type { MapLine, MapPoint } from "@/components/MapView";
import { routeLine, type LatLng } from "@/lib/polyline";

export type EditorStop = {
  id: string;
  lat: number;
  lng: number;
  name: string;
  address: string;
  eta: string | null;
};

export type StopMapInput = {
  start: LatLng;
  stops: EditorStop[]; // current order
  order: string[]; // draft order (stop ids)
  currentGeometry?: string | null;
  draftGeometry?: string | null; // road geometry of the draft when it came from the optimiser
};

/** Points and lines for the comparison map, and whether the draft differs from the current order. */
export function stopOrderMap({ start, stops, order, currentGeometry, draftGeometry }: StopMapInput) {
  const byId = new Map(stops.map((stop) => [stop.id, stop]));
  const draft = order.map((id) => byId.get(id)).filter((stop): stop is EditorStop => Boolean(stop));
  const changed = order.some((id, index) => id !== stops[index]?.id);
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
  const draftLine = draftGeometry ? routeLine(draftGeometry, []) : [start, ...draft.map((stop): LatLng => [stop.lat, stop.lng])];
  const lines: MapLine[] = changed
    ? [
        { id: "current", positions: currentLine, color: "#f8183e", dashed: true },
        { id: "draft", positions: draftLine },
      ]
    : [{ id: "current", positions: currentLine }];
  return { points, lines, changed, draft };
}
