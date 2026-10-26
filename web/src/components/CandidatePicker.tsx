// CandidatePicker - H-07: replacement drivers on a map and in a ranked list, then a
// confirmation step. Used by order reassignment and by incident resolution.

import { useState } from "react";
import { MapLegend, MapView, type MapPoint } from "@/components/MapView";
import { Alert, Badge, Button, EmptyState, Loading } from "@/components/ui";
import { cn } from "@/lib/cn";
import { errorMessage } from "@/lib/errors";
import { formatKm } from "@/lib/format";
import type { Candidate } from "@/types";

type Props = {
  candidates: Candidate[] | undefined;
  loading: boolean;
  // Where the parcels are collected: the hub, or the incident location for a hand-over.
  origin: { lat: number; lng: number; label: string; kind: "hub" | "incident" } | null;
  submitting: boolean;
  error: unknown;
  confirmLabel?: (name: string) => string;
  onConfirm: (candidate: Candidate) => void;
};

export function CandidatePicker({
  candidates,
  loading,
  origin,
  submitting,
  error,
  confirmLabel = (name) => `Send offer to ${name}`,
  onConfirm,
}: Props) {
  const [chosen, setChosen] = useState<Candidate | null>(null);

  if (loading) return <Loading label="Looking for available drivers..." />;
  if (!candidates?.length) {
    return (
      <EmptyState title="No driver available right now">
        Drivers must be online, on shift today and free of other offers. Try again in a moment or hold the order at the hub.
      </EmptyState>
    );
  }

  const points: MapPoint[] = candidates
    .filter((candidate) => candidate.lat !== null && candidate.lng !== null)
    .map((candidate) => ({
      id: candidate.driver_id,
      lat: candidate.lat as number,
      lng: candidate.lng as number,
      label: `${candidate.name} - ${formatKm(candidate.distance_km)}`,
      kind: chosen?.driver_id === candidate.driver_id ? "selected" : "candidate",
      onClick: () => setChosen(candidate),
    }));
  if (origin) points.push({ id: "origin", ...origin });

  return (
    <div className="flex flex-col gap-3">
      <MapView points={points} className="h-64" />
      <MapLegend kinds={origin ? [origin.kind, "candidate"] : ["candidate"]} />
      <ul className="flex flex-col gap-2">
        {candidates.map((candidate, index) => (
          <li key={candidate.driver_id}>
            <button
              type="button"
              onClick={() => setChosen(candidate)}
              className={cn(
                "flex w-full items-center justify-between gap-3 rounded-input border px-4 py-3 text-left text-sm",
                chosen?.driver_id === candidate.driver_id
                  ? "border-primary-600 bg-primary-50"
                  : "border-line bg-white hover:border-primary-200",
              )}
            >
              <span>
                <span className="font-semibold">{candidate.name}</span>
                {index === 0 && (
                  <span className="ml-2">
                    <Badge tone="success">Best match</Badge>
                  </span>
                )}
                <span className="block text-xs text-neutral-600">
                  {formatKm(candidate.distance_km)} away - {candidate.active_orders} active order
                  {candidate.active_orders === 1 ? "" : "s"}
                </span>
              </span>
              <span className="text-right">
                <span className="block font-display text-lg font-bold text-primary-700">{Math.round(candidate.score)}</span>
                <span className="text-xs text-neutral-500">score</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
      {Boolean(error) && <Alert tone="danger">{errorMessage(error)}</Alert>}
      <Button disabled={!chosen} loading={submitting} onClick={() => chosen && onConfirm(chosen)}>
        {chosen ? confirmLabel(chosen.name) : "Choose a driver"}
      </Button>
      <p className="text-xs text-neutral-500">
        The driver has a short time to accept. If they decline, you can choose someone else.
      </p>
    </div>
  );
}
