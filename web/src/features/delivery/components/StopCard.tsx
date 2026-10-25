// StopCard - one stop of today's route (D-07): order in the sequence, customer, ETA, parcels

import { Link } from "react-router";
import { Badge } from "@/components/ui";
import { formatClock } from "@/lib/format";
import type { RouteStop } from "@/types";

export function StopCard({ stop, position }: { stop: RouteStop; position: number }) {
  const late = stop.orders.some((order) => order.current_eta && order.current_eta > order.promised_at);
  const express = stop.orders.some((order) => order.priority === "EXPRESS");
  return (
    <Link
      to={`/driver/stops/${stop.id}`}
      className="flex gap-3 rounded-card border border-line bg-white p-4 transition-colors hover:border-primary-200"
    >
      <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary-600 text-sm font-bold text-white">
        {position}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <p className="truncate font-semibold text-primary-700">{stop.recipient_name}</p>
          <p className="shrink-0 text-sm font-semibold">{formatClock(stop.eta)}</p>
        </div>
        <p className="truncate text-sm text-neutral-600">{stop.address}</p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          <Badge tone="primary">
            {stop.orders.length} parcel{stop.orders.length === 1 ? "" : "s"}
          </Badge>
          {express && <Badge tone="danger">Express</Badge>}
          {late && <Badge tone="warning">Behind schedule</Badge>}
        </div>
      </div>
    </Link>
  );
}
