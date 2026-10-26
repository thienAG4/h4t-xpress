// StopOrderEditor - reorder pending stops with Up/Down and compare the routes on a map
// (H-02 route planning, H-08 reroute). The current route is red and dashed, the new one blue.
// The map data and the list are also exported apart, for screens that place them separately.

import { ChevronDown, ChevronUp, MapPin } from "lucide-react";
import { MapView } from "@/components/MapView";
import { IconTile } from "@/components/ui";
import { formatClock } from "@/lib/format";
import { stopOrderMap, type EditorStop, type StopMapInput } from "@/lib/stopOrder";

export type { EditorStop } from "@/lib/stopOrder";

const MOVE_BUTTON =
  "grid size-8 place-items-center rounded-md border border-line text-neutral-600 hover:border-primary-200 hover:text-primary-600 disabled:cursor-not-allowed disabled:opacity-35";

/** Draft order as Figma route rows: pin tile, stop name and address, estimate time, Up/Down. */
export function StopOrderList({
  stops,
  order,
  onChange,
}: {
  stops: EditorStop[];
  order: string[];
  onChange: (order: string[]) => void;
}) {
  const byId = new Map(stops.map((stop) => [stop.id, stop]));
  const draft = order.map((id) => byId.get(id)).filter((stop): stop is EditorStop => Boolean(stop));
  const move = (index: number, offset: -1 | 1) => {
    const next = [...order];
    [next[index], next[index + offset]] = [next[index + offset], next[index]];
    onChange(next);
  };

  return (
    <ol className="flex flex-col">
      {draft.map((stop, index) => (
        <li key={stop.id} className="flex items-center gap-3 border-b border-line py-3 text-sm last:border-b-0">
          <IconTile icon={MapPin} size="sm" tone="neutral" />
          <span className="min-w-0 flex-1">
            <span className="block truncate font-medium text-ink">
              Stop {index + 1}: {stop.name}
            </span>
            <span className="block truncate text-xs text-neutral-500">{stop.address}</span>
          </span>
          <span className="shrink-0 text-right text-xs text-neutral-500">
            Estimate
            <span className="block text-sm font-medium text-ink tabular-nums">{formatClock(stop.eta)}</span>
          </span>
          <span className="flex shrink-0 gap-1">
            <button
              type="button"
              className={MOVE_BUTTON}
              disabled={index === 0}
              onClick={() => move(index, -1)}
              aria-label={`Move ${stop.name} up`}
            >
              <ChevronUp className="size-4" aria-hidden />
            </button>
            <button
              type="button"
              className={MOVE_BUTTON}
              disabled={index === draft.length - 1}
              onClick={() => move(index, 1)}
              aria-label={`Move ${stop.name} down`}
            >
              <ChevronDown className="size-4" aria-hidden />
            </button>
          </span>
        </li>
      ))}
    </ol>
  );
}

export function StopOrderEditor({
  className,
  onChange,
  ...input
}: StopMapInput & { onChange: (order: string[]) => void; className?: string }) {
  const { points, lines, changed } = stopOrderMap(input);
  return (
    <div className={className}>
      <MapView points={points} lines={lines} showLabels className="h-72" />
      {changed && <p className="mt-2 text-xs text-neutral-600">Dashed red: current order. Blue: new order.</p>}
      <div className="mt-2">
        <StopOrderList stops={input.stops} order={input.order} onChange={onChange} />
      </div>
    </div>
  );
}
