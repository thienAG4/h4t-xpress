// MapView - OpenStreetMap base map with circle markers and straight route lines.
// Markers are drawn shapes, never images, so the map follows the no-icon rule.

import "leaflet/dist/leaflet.css";
import type { LatLngTuple } from "leaflet";
import { useEffect } from "react";
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip, useMap } from "react-leaflet";
import { cn } from "@/lib/cn";

export type PointKind = "hub" | "driver" | "stop" | "incident" | "candidate" | "selected";

export type MapPoint = {
  id: string;
  lat: number;
  lng: number;
  label: string;
  kind: PointKind;
  // Short text shown inside the label permanently (stop number, driver initials).
  tag?: string;
  onClick?: () => void;
};

export type MapLine = { id: string; positions: LatLngTuple[]; color?: string; dashed?: boolean };

// Figma: blue route line, orange-red stop pins, dark hub. Green marks a free candidate.
const STYLE: Record<PointKind, { color: string; radius: number }> = {
  hub: { color: "#0a479f", radius: 10 },
  driver: { color: "#1070f8", radius: 9 },
  stop: { color: "#f2602b", radius: 8 },
  incident: { color: "#f8183e", radius: 11 },
  candidate: { color: "#22c55e", radius: 9 },
  selected: { color: "#1070f8", radius: 12 },
};

const MAP_LEGEND: { kind: PointKind; label: string }[] = [
  { kind: "hub", label: "Hub" },
  { kind: "driver", label: "Driver" },
  { kind: "stop", label: "Stop" },
  { kind: "incident", label: "Incident" },
  { kind: "candidate", label: "Available driver" },
];

const HCM_CENTER: LatLngTuple = [10.85, 106.75];

// OpenStreetMap tiles served by FOSSGIS (openstreetmap.de). Some Vietnamese ISP resolvers do
// not answer for tile.openstreetmap.org; this mirror needs no API key and resolves fine.
const TILES = "https://tile.openstreetmap.de/{z}/{x}/{y}.png";
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

/** Fit the view when the set of points changes, not on every render (keeps the user's pan). */
function FitToPoints({ signature }: { signature: string }) {
  const map = useMap();
  useEffect(() => {
    const points = signature
      .split(";")
      .filter(Boolean)
      .map((pair) => pair.split(",").map(Number) as LatLngTuple);
    if (points.length === 1) map.setView(points[0], 14);
    if (points.length > 1) map.fitBounds(points, { padding: [36, 36], maxZoom: 15 });
  }, [map, signature]);
  return null;
}

type Props = {
  points: MapPoint[];
  lines?: MapLine[];
  className?: string;
  showLabels?: boolean;
};

export function MapView({ points, lines = [], className, showLabels = false }: Props) {
  const signature = points.map((point) => `${point.lat.toFixed(5)},${point.lng.toFixed(5)}`).join(";");
  return (
    // `isolate` keeps Leaflet's high z-index panes under sticky headers and dialogs.
    <div className={cn("map-view isolate overflow-hidden rounded-card border border-line", className)}>
      {/* No wheel zoom: the page keeps scrolling over the map; +/- and pinch still zoom. */}
      <MapContainer center={HCM_CENTER} zoom={12} scrollWheelZoom={false} className="h-full w-full">
        <TileLayer attribution={ATTRIBUTION} url={TILES} maxZoom={18} />
        {lines.map((line) => (
          <Polyline
            key={line.id}
            positions={line.positions}
            pathOptions={{ color: line.color ?? "#1070f8", weight: 4, dashArray: line.dashed ? "6 8" : undefined }}
          />
        ))}
        {points.map((point) => {
          const style = STYLE[point.kind];
          return (
            <CircleMarker
              key={point.id}
              center={[point.lat, point.lng]}
              radius={style.radius}
              pathOptions={{ color: "#ffffff", weight: 2, fillColor: style.color, fillOpacity: 1 }}
              eventHandlers={point.onClick ? { click: point.onClick } : undefined}
            >
              <Tooltip direction="top" offset={[0, -8]} permanent={showLabels && Boolean(point.tag)}>
                {showLabels && point.tag ? point.tag : point.label}
              </Tooltip>
            </CircleMarker>
          );
        })}
        <FitToPoints signature={signature} />
      </MapContainer>
    </div>
  );
}

export function MapLegend({ kinds }: { kinds: PointKind[] }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-neutral-600">
      {MAP_LEGEND.filter((item) => kinds.includes(item.kind)).map((item) => (
        <li key={item.kind} className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full" style={{ backgroundColor: STYLE[item.kind].color }} />
          {item.label}
        </li>
      ))}
    </ul>
  );
}
