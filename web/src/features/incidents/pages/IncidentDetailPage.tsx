// IncidentDetailPage - H-06 laid out like the Figma "Issue Report", with the resolution flows
// H-07 and H-08: read the report, classify (BR13), answer the driver (BR14), then apply a
// solution (BR15) in the "Resolution action" box under the report.

import { CircleCheck, Route, UserRoundCheck, Warehouse } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, useParams } from "react-router";
import { CandidatePicker } from "@/components/CandidatePicker";
import { MapLegend, MapView, type MapPoint } from "@/components/MapView";
import { PageHeader } from "@/components/PageHeader";
import { IncidentStatusBadge, OrderStatusBadge, PriorityBadge } from "@/components/StatusBadge";
import { Alert, Badge, Button, Dialog, IconTile, Loading, SelectField, TextAreaField, TextField } from "@/components/ui";
import { cn } from "@/lib/cn";
import { errorMessage } from "@/lib/errors";
import { formatClock, formatDateTime, formatPhone } from "@/lib/format";
import { CATEGORY, INCIDENT_TYPE, PRIORITY, SOLUTION, options } from "@/lib/labels";
import type { Incident, IncidentCategory, IncidentPriority, ResolutionSolution, ResolveInput } from "@/types";
import { ReroutePanel } from "../components/ReroutePanel";
import { useCandidates, useClassify, useIncident, useResolve, useRespond } from "../hooks";

const STATUS_DOT: Record<Incident["status"], string> = {
  OPEN: "bg-primary-500",
  IN_REVIEW: "bg-[#f8c47a]",
  RESOLVING: "bg-warning-500",
  RESOLVED: "bg-success-500",
  CLOSED_NO_ACTION: "bg-neutral-400",
};

const SOLUTION_ICON: Record<ResolutionSolution, typeof Route> = {
  ROUTE_SUGGESTED: Route,
  DRIVER_REASSIGNMENT: UserRoundCheck,
  HOLD_AT_HUB: Warehouse,
};

function ReportSection({ incident }: { incident: Incident }) {
  const located = incident.lat !== null && incident.lng !== null;
  const mapPoints: MapPoint[] = located
    ? [{ id: "incident", lat: incident.lat as number, lng: incident.lng as number, label: "Reported here", kind: "incident" }]
    : [];

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <span className={cn("size-4 rounded-full", STATUS_DOT[incident.status])} aria-hidden />
          <span className="text-lg font-medium text-ink">{incident.code}</span>
          <IncidentStatusBadge status={incident.status} />
          <PriorityBadge priority={incident.priority} />
        </div>
        <span className="text-sm text-neutral-500">Posted at {formatDateTime(incident.reported_at)}</span>
      </div>
      <div className="mt-5 grid gap-6 md:grid-cols-[minmax(0,1fr)_320px]">
        <div>
          <h2 className="font-sans text-xl font-medium text-ink">{INCIDENT_TYPE[incident.type]}</h2>
          <p className="mt-3 text-[15px] whitespace-pre-line text-neutral-600">{incident.description}</p>
          {incident.photo_urls.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {incident.photo_urls.map((url) => (
                <a key={url} href={url} target="_blank" rel="noreferrer">
                  <img src={url} alt="Evidence from the driver" className="size-28 rounded-md border border-line object-cover" />
                </a>
              ))}
            </div>
          )}
        </div>
        {located && (
          <div className="flex flex-col gap-2">
            <MapView points={mapPoints} className="h-44 rounded-lg" />
            <MapLegend kinds={["incident"]} />
          </div>
        )}
      </div>
    </div>
  );
}

function AffectedOrders({ incident }: { incident: Incident }) {
  return (
    <section>
      <h3 className="font-sans text-base font-medium text-ink">Parcels affected ({incident.orders.length})</h3>
      <ul className="mt-2 flex flex-col divide-y divide-line">
        {incident.orders.map((order) => (
          <li key={order.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
            <div>
              <Link to={`/hub/tracking/${order.id}`} className="font-medium text-ink hover:text-primary-600">
                {order.waybill_code}
              </Link>
              {order.priority === "EXPRESS" && (
                <span className="ml-2">
                  <Badge tone="danger">Express</Badge>
                </span>
              )}
              <p className="text-xs text-neutral-500">
                {order.recipient_name} - {order.delivery_address}
              </p>
            </div>
            <div className="text-right">
              <OrderStatusBadge status={order.status} />
              <p className="mt-1 text-xs text-neutral-500">
                Promised {formatClock(order.promised_at)} - ETA {formatClock(order.current_eta)}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Step({ title, done, children }: { title: string; done: boolean; children: ReactNode }) {
  return (
    <section className="border-t border-line pt-5 first:border-t-0 first:pt-0">
      <h4 className="flex items-center gap-2 font-sans text-[15px] font-medium text-ink">
        {done && <CircleCheck className="size-4 text-success-700" aria-label="Done" />}
        {title}
      </h4>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function ResolutionCard({ incident, onResolved }: { incident: Incident; onResolved: (message: string) => void }) {
  const classify = useClassify(incident.id);
  const respond = useRespond(incident.id);
  const resolve = useResolve(incident.id);
  const [category, setCategory] = useState<IncidentCategory>(incident.category ?? incident.suggested_category ?? "OBJECTIVE");
  const [priority, setPriority] = useState<IncidentPriority>(incident.priority ?? "MEDIUM");
  const [message, setMessage] = useState(incident.hub_response ?? "");
  const [solution, setSolution] = useState<ResolutionSolution>(
    (incident.category ?? incident.suggested_category) === "SUBJECTIVE" ? "DRIVER_REASSIGNMENT" : "ROUTE_SUGGESTED",
  );
  const [holdNote, setHoldNote] = useState("");
  // mutateAsync: the result dialog lives in the page and must open even after a refetch.
  const apply = (data: ResolveInput, message: string) =>
    void resolve.mutateAsync(data).then(() => onResolved(message), () => undefined);
  const editable = incident.status === "OPEN" || incident.status === "IN_REVIEW";
  const ready = Boolean(incident.category && incident.hub_response);
  const candidates = useCandidates(incident.id, editable && ready && solution === "DRIVER_REASSIGNMENT");
  const origin =
    incident.lat !== null && incident.lng !== null
      ? { lat: incident.lat, lng: incident.lng, label: "Parcels are here", kind: "incident" as const }
      : null;

  return (
    <section className="rounded-lg border border-line bg-neutral-50/70 p-6">
      <h3 className="font-sans text-lg font-medium text-ink">Resolution action</h3>
      <div className="mt-5 flex flex-col gap-5">
        <Step title="Classify" done={Boolean(incident.category)}>
          <div className="grid gap-4 md:grid-cols-3">
            <TextField compact readOnly label="Driver contact" value={`${incident.driver.name} - ${formatPhone(incident.driver.phone)}`} />
            <SelectField
              compact
              label="Incident category"
              options={options(CATEGORY)}
              value={category}
              disabled={!editable}
              onChange={(event) => setCategory(event.target.value as IncidentCategory)}
              hint={CATEGORY[category].hint}
            />
            <SelectField
              compact
              label="Priority"
              options={options(PRIORITY)}
              value={priority}
              disabled={!editable}
              onChange={(event) => setPriority(event.target.value as IncidentPriority)}
            />
          </div>
          {incident.suggested_category && !incident.category && (
            <p className="mt-2 text-xs text-neutral-600">
              Suggested from the report type: {CATEGORY[incident.suggested_category].label}.
            </p>
          )}
          {classify.isError && <Alert tone="danger" className="mt-2">{errorMessage(classify.error)}</Alert>}
          {editable && (
            <Button size="sm" className="mt-3" loading={classify.isPending} onClick={() => classify.mutate({ category, priority })}>
              {incident.category ? "Update classification" : "Save classification"}
            </Button>
          )}
        </Step>

        <Step title="Answer the driver" done={Boolean(incident.hub_response)}>
          <TextAreaField
            label="Manager response"
            rows={3}
            placeholder="e.g. Stay where you are. Driver B will collect the parcels within 20 minutes."
            value={message}
            disabled={!editable}
            onChange={(event) => setMessage(event.target.value)}
          />
          {respond.isError && <Alert tone="danger" className="mt-2">{errorMessage(respond.error)}</Alert>}
          {editable && (
            <Button
              size="sm"
              className="mt-3"
              disabled={!incident.category || message.trim().length < 3}
              loading={respond.isPending}
              onClick={() => respond.mutate(message.trim())}
            >
              Send to driver
            </Button>
          )}
          {!incident.category && editable && <p className="mt-2 text-xs text-neutral-500">Classify the incident first.</p>}
        </Step>

        <Step title="Solution" done={incident.status === "RESOLVED"}>
          {!editable && (
            <Alert tone={incident.status === "RESOLVED" ? "success" : "info"}>
              {incident.status === "RESOLVING"
                ? "Waiting for the replacement driver to accept. If they decline, the incident comes back here."
                : "This incident is closed."}
            </Alert>
          )}
          {editable && !ready && <p className="text-sm text-neutral-600">Classify and answer the driver to unlock the solutions.</p>}
          {editable && ready && (
            <div className="flex flex-col gap-4">
              <div className="grid gap-3 sm:grid-cols-3">
                {(Object.keys(SOLUTION) as ResolutionSolution[]).map((key) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setSolution(key)}
                    aria-pressed={solution === key}
                    className={cn(
                      "flex items-start gap-3 rounded-lg border bg-white px-3 py-3 text-left text-sm",
                      solution === key ? "border-2 border-primary-600" : "border-line hover:border-primary-200",
                    )}
                  >
                    <IconTile icon={SOLUTION_ICON[key]} size="sm" tone={solution === key ? "primary" : "neutral"} />
                    <span>
                      <span className="block font-medium text-ink">{SOLUTION[key].label}</span>
                      <span className="text-xs text-neutral-600">{SOLUTION[key].hint}</span>
                    </span>
                  </button>
                ))}
              </div>

              {solution === "DRIVER_REASSIGNMENT" && (
                <CandidatePicker
                  candidates={candidates.data}
                  loading={candidates.isPending}
                  origin={origin}
                  submitting={resolve.isPending}
                  error={resolve.error}
                  confirmLabel={(name) => `Ask ${name} to take over`}
                  onConfirm={(candidate) =>
                    apply(
                      { solution, driver_id: candidate.driver_id },
                      `Offer sent to ${candidate.name}. The incident closes when they accept.`,
                    )
                  }
                />
              )}
              {solution === "ROUTE_SUGGESTED" && (
                <ReroutePanel
                  driverId={incident.driver.id}
                  submitting={resolve.isPending}
                  error={resolve.error}
                  onSubmit={(stopIds, note) =>
                    apply(
                      { solution, stop_ids: stopIds, note },
                      "The new route was sent to the driver and the ETAs were updated.",
                    )
                  }
                />
              )}
              {solution === "HOLD_AT_HUB" && (
                <div className="flex flex-col gap-3">
                  <TextAreaField label="Note (optional)" rows={2} value={holdNote} onChange={(event) => setHoldNote(event.target.value)} />
                  {resolve.isError && <Alert tone="danger">{errorMessage(resolve.error)}</Alert>}
                  <Button
                    variant="danger"
                    loading={resolve.isPending}
                    onClick={() =>
                      apply(
                        { solution, note: holdNote.trim() || null },
                        "The parcels are on hold at the hub. Release them later from the order page.",
                      )
                    }
                  >
                    Hold parcels at the hub
                  </Button>
                </div>
              )}
            </div>
          )}
        </Step>

        {incident.resolutions.length > 0 && (
          <section className="border-t border-line pt-5">
            <h4 className="font-sans text-[15px] font-medium text-ink">Decisions</h4>
            <ul className="mt-2 flex flex-col gap-2 text-sm">
              {incident.resolutions.map((resolution) => (
                <li key={resolution.decided_at} className="flex justify-between gap-3">
                  <span>
                    {SOLUTION[resolution.solution].label}
                    {resolution.new_driver_name ? ` to ${resolution.new_driver_name}` : ""}
                    <span className="block text-xs text-neutral-500">{formatDateTime(resolution.decided_at)}</span>
                  </span>
                  <Badge tone={resolution.status === "DONE" ? "success" : resolution.status === "FAILED" ? "danger" : "warning"}>
                    {resolution.status === "DONE" ? "Done" : resolution.status === "FAILED" ? "Declined" : "Pending"}
                  </Badge>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </section>
  );
}

export function IncidentDetailPage() {
  const { incidentId = "" } = useParams();
  const incident = useIncident(incidentId);
  // Lives here: the resolution card remounts when the status changes.
  const [result, setResult] = useState<string | null>(null);

  if (incident.isPending) return <Loading />;
  if (incident.isError) return <Alert tone="danger">{errorMessage(incident.error)}</Alert>;
  const data = incident.data;

  return (
    <>
      <PageHeader
        title="Issue report"
        description={`Reported by ${data.driver.name}${data.handled_by ? `, handled by ${data.handled_by}` : ""}.`}
        actions={
          <Link to="/hub/incidents/list" className="inline-flex h-10 items-center rounded-lg border border-line bg-white px-4 text-sm font-medium hover:border-primary-200">
            All incidents
          </Link>
        }
      />
      <div className="flex flex-col gap-6 rounded-lg border border-line bg-white p-6">
        <ReportSection incident={data} />
        <AffectedOrders incident={data} />
        {/* Keyed by incident only: a status change must not wipe what the manager is typing. */}
        <ResolutionCard key={data.id} incident={data} onResolved={setResult} />
      </div>
      <Dialog
        open={Boolean(result)}
        title="SUCCESS!"
        onClose={() => setResult(null)}
        actions={<Button onClick={() => setResult(null)}>Back</Button>}
      >
        {result}
      </Dialog>
    </>
  );
}
