// MyIncidentsPage - the driver's reports with the hub's answer and the chosen solution (BR14)

import { Link } from "react-router";
import { ScreenTitle } from "@/components/ScreenTitle";
import { IncidentStatusBadge } from "@/components/StatusBadge";
import { Alert, Card, EmptyState, Loading } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { INCIDENT_TYPE } from "@/lib/labels";
import type { Incident } from "@/types";
import { useMyIncidents } from "../hooks";

// What the driver should do once the hub has decided.
function nextStep(incident: Incident): string | null {
  const last = incident.resolutions[0];
  if (!last) return null;
  if (last.solution === "ROUTE_SUGGESTED") return "Your route was reordered. Follow the new stop order.";
  if (last.solution === "HOLD_AT_HUB") return "Bring the parcels back to the hub.";
  if (last.status === "PENDING") return `Waiting for ${last.new_driver_name ?? "another driver"} to accept your parcels.`;
  if (last.status === "DONE") return `${last.new_driver_name ?? "Another driver"} will collect the parcels from you.`;
  return "The replacement driver declined. The hub is choosing someone else.";
}

export function MyIncidentsPage() {
  const incidents = useMyIncidents();

  return (
    <div className="flex flex-col gap-4">
      <ScreenTitle title="My incidents" />
      <Link
        to="/driver/incidents/new"
        className="inline-flex h-[50px] items-center justify-center rounded-button bg-danger-500 font-display font-bold text-white"
      >
        Report an issue
      </Link>

      {incidents.isPending && <Loading />}
      {incidents.isError && <Alert tone="danger">{errorMessage(incidents.error)}</Alert>}
      {incidents.data?.length === 0 && <EmptyState title="No incidents reported" />}
      {incidents.data?.map((incident) => {
        const step = nextStep(incident);
        return (
          <Card key={incident.id} className="p-4">
            <div className="flex items-center justify-between gap-2">
              <p className="font-display font-bold">{incident.code}</p>
              <IncidentStatusBadge status={incident.status} />
            </div>
            <p className="text-sm font-semibold text-primary-700">{INCIDENT_TYPE[incident.type]}</p>
            <p className="text-xs text-neutral-500">{formatDateTime(incident.reported_at)}</p>
            <p className="mt-2 text-sm text-neutral-700">{incident.description}</p>
            <p className="mt-1 text-xs text-neutral-600">
              Parcels: {incident.orders.map((order) => order.waybill_code).join(", ")}
            </p>
            {incident.hub_response && (
              <div className="mt-3 rounded-input bg-primary-50 px-3 py-2 text-sm">
                <p className="text-xs font-semibold text-primary-700">Hub answer</p>
                <p>{incident.hub_response}</p>
              </div>
            )}
            {step && <p className="mt-2 text-sm font-semibold">{step}</p>}
          </Card>
        );
      })}
    </div>
  );
}
