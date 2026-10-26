// OrderPanel - right column of H-03 drawn like the Figma "Status" and "Vehicle Details" cards:
// delivery progress bar, status timeline, the manual actions available in the order's current
// status, delivery data and attempts.

import { useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { Link } from "react-router";
import { CandidatePicker } from "@/components/CandidatePicker";
import { OrderStatusBadge } from "@/components/StatusBadge";
import { Timeline } from "@/components/Timeline";
import { Alert, Avatar, Badge, Button, Dialog, Panel, SelectField } from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatClock, formatDateTime, formatMoney, formatPhone } from "@/lib/format";
import { FAILURE_REASON } from "@/lib/labels";
import { hasPermission, useSession } from "@/lib/session";
import type { HubOrderDetail, OrderStatus } from "@/types";
import { useConfirmReturned, useHold, useOrderCandidates, useReassign, useReleaseHold } from "../hooks";

const HOLD_REASONS = ["Address needs checking", "Customer asked to wait", "Parcel needs repacking", "No driver available"].map(
  (value) => ({ value, label: value }),
);
const REASSIGNABLE = new Set(["AWAITING_ASSIGNMENT", "ASSIGNED", "ON_HOLD"]);

// Where each status sits on the progress bar (Figma: the cities along the route).
const STEPS = ["Received", "Assigned", "Picked up", "On road", "Delivered"];
const STEP_OF: Partial<Record<OrderStatus, number>> = {
  AWAITING_ASSIGNMENT: 0,
  ON_HOLD: 0,
  RESCHEDULED: 0,
  ASSIGNED: 1,
  PICKED_UP: 2,
  OUT_FOR_DELIVERY: 3,
  DELIVERY_FAILED: 3,
  RETURNING: 3,
  DELIVERED: 4,
  RETURNED_TO_HUB: 4,
  CANCELLED: 4,
};
const PROBLEM: OrderStatus[] = ["ON_HOLD", "DELIVERY_FAILED", "RETURNING", "RETURNED_TO_HUB", "CANCELLED"];

function ProgressBar({ order }: { order: HubOrderDetail }) {
  const step = STEP_OF[order.status] ?? 0;
  const share = ((step + 1) / STEPS.length) * 100;
  const problem = PROBLEM.includes(order.status);
  const note =
    order.status === "DELIVERED"
      ? "Delivered"
      : order.current_eta
        ? `ETA ${formatClock(order.current_eta)}${order.eta_is_estimate ? " (estimate)" : ""}`
        : "No ETA yet";
  return (
    <div>
      <div className="grid grid-cols-5 text-xs text-neutral-500">
        {STEPS.map((label, index) => (
          <span key={label} className={cn(index === step && "font-semibold text-primary-700", index === 4 && "text-right")}>
            {label}
          </span>
        ))}
      </div>
      <div
        className="relative mt-2 h-9 overflow-hidden rounded-md bg-neutral-100"
        role="img"
        aria-label={`Progress: ${STEPS[step]}, ${note}`}
      >
        <div
          className={cn(
            "h-full rounded-md bg-gradient-to-r",
            problem ? "from-danger-700 to-danger-500" : "from-primary-800 via-primary-600 to-primary-500",
          )}
          style={{ width: `${share}%` }}
        />
        {[1, 2, 3, 4].map((index) => (
          <span
            key={index}
            className="absolute top-0 h-full border-l border-dashed border-white/70"
            style={{ left: `${index * 20}%` }}
            aria-hidden
          />
        ))}
        {/* The note sits on the empty part of the bar, or inside the fill once it is long. */}
        <span
          className={cn(
            "absolute top-1/2 -translate-y-1/2 text-sm font-medium",
            share >= 60 ? "left-3 text-white" : "right-3 text-ink",
          )}
        >
          {note}
        </span>
      </div>
    </div>
  );
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-neutral-500">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium text-ink">{children}</dd>
    </div>
  );
}

export function OrderPanel({ order }: { order: HubOrderDetail }) {
  const user = useSession((state) => state.user);
  const canAct = hasPermission(user, "order.reassign");
  const [dialog, setDialog] = useState<"reassign" | "hold" | null>(null);
  const [holdReason, setHoldReason] = useState(HOLD_REASONS[0].value);
  const reassign = useReassign();
  const hold = useHold();
  const release = useReleaseHold();
  const returned = useConfirmReturned();
  const candidates = useOrderCandidates(order.id, dialog === "reassign");

  const queryClient = useQueryClient();
  const incidentOpen = Boolean(order.incident_id);
  const pickup = { lat: order.hub_lat, lng: order.hub_lng, label: "Pickup at the hub", kind: "hub" as const };

  return (
    <div className="flex flex-col gap-4">
      <Panel
        title="Status"
        action={
          <Button
            size="sm"
            variant="secondary"
            onClick={() => void queryClient.invalidateQueries({ queryKey: ["hub", "order", order.id] })}
          >
            Refresh
          </Button>
        }
        bodyClassName="flex flex-col gap-4"
      >
        <ProgressBar order={order} />
        {order.at_risk && (
          <Alert tone="danger">
            SLA risk: ETA {formatDateTime(order.current_eta)} is after the promised {formatDateTime(order.promised_at)}.
          </Alert>
        )}
        {incidentOpen && (
          <Alert tone="warning">
            This order is part of an open incident.{" "}
            <Link to={`/hub/incidents/${order.incident_id}`} className="font-semibold underline">
              Handle it there
            </Link>
            .
          </Alert>
        )}
        <Timeline events={order.timeline} />
      </Panel>

      {canAct && !incidentOpen && (
        <Panel title="Actions">
          <div className="flex flex-wrap gap-2">
            {REASSIGNABLE.has(order.status) && (
              <Button size="sm" onClick={() => setDialog("reassign")}>
                {order.driver ? "Reassign driver" : "Choose a driver"}
              </Button>
            )}
            {order.status === "AWAITING_ASSIGNMENT" && (
              <Button size="sm" variant="secondary" onClick={() => setDialog("hold")}>
                Hold at hub
              </Button>
            )}
            {order.status === "ON_HOLD" && (
              <Button size="sm" variant="secondary" loading={release.isPending} onClick={() => release.mutate(order.id)}>
                Release to dispatch
              </Button>
            )}
            {order.status === "RETURNING" && (
              <Button size="sm" variant="secondary" loading={returned.isPending} onClick={() => returned.mutate(order.id)}>
                Confirm parcel is back
              </Button>
            )}
            {!REASSIGNABLE.has(order.status) && order.status !== "RETURNING" && (
              <p className="text-sm text-neutral-600">
                {order.status === "PICKED_UP" || order.status === "OUT_FOR_DELIVERY"
                  ? "The parcel is with the driver. Problems on the road come in as incidents."
                  : "No action needed in this status."}
              </p>
            )}
          </div>
        </Panel>
      )}

      <Panel title="Delivery details" action={<OrderStatusBadge status={order.status} />}>
        <div className="flex items-start gap-3">
          <Avatar name={order.recipient_name} size="lg" />
          <div className="min-w-0">
            <p className="text-base font-semibold text-ink">{order.recipient_name}</p>
            <p className="text-sm text-neutral-600">{formatPhone(order.recipient_phone)}</p>
            <p className="mt-1 text-xs text-neutral-500">{order.delivery_address}</p>
          </div>
          {order.priority === "EXPRESS" && (
            <span className="ml-auto">
              <Badge tone="danger">Express</Badge>
            </span>
          )}
        </div>
        <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 border-t border-line pt-4">
          <Fact label="Driver">
            {order.driver ? order.driver.name : "Not assigned"}
            {order.driver?.phone && (
              <span className="block text-xs font-normal text-neutral-600">{formatPhone(order.driver.phone)}</span>
            )}
            {order.handover_from && (
              <span className="block text-xs font-normal text-warning-700">Hand-over from {order.handover_from}</span>
            )}
          </Fact>
          <Fact label="Promised">{formatDateTime(order.promised_at)}</Fact>
          <Fact label="Parcel">{order.items.map((item) => `${item.name} x${item.qty}`).join(", ")}</Fact>
          <Fact label="Weight">{Number(order.weight_kg)} kg</Fact>
          <Fact label="Cash to collect">{formatMoney(order.cod_amount)}</Fact>
          <Fact label="Created">{formatDateTime(order.created_at)}</Fact>
        </dl>
      </Panel>

      {order.attempts.length > 0 && (
        <Panel title="Delivery attempts">
          <ul className="flex flex-col gap-3">
            {order.attempts.map((attempt) => (
              <li key={attempt.attempted_at} className="text-sm">
                <p className="font-semibold">
                  {attempt.outcome === "DELIVERED" ? "Delivered" : FAILURE_REASON[attempt.failure_reason ?? "OTHER"]}
                </p>
                <p className="text-xs text-neutral-600">{formatDateTime(attempt.attempted_at)}</p>
                {attempt.note && <p className="text-xs">{attempt.note}</p>}
                <div className="mt-2 flex gap-2">
                  {attempt.photo_urls.map((url) => (
                    <a key={url} href={url} target="_blank" rel="noreferrer">
                      <img src={url} alt="Proof of delivery" className="size-16 rounded-md border border-line object-cover" />
                    </a>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      <Dialog open={dialog === "reassign"} title={`Choose a driver for ${order.waybill_code}`} onClose={() => setDialog(null)}>
        <CandidatePicker
          candidates={candidates.data}
          loading={candidates.isPending}
          origin={pickup}
          submitting={reassign.isPending}
          error={reassign.error}
          onConfirm={(candidate) =>
            reassign.mutate({ orderId: order.id, driverId: candidate.driver_id }, { onSuccess: () => setDialog(null) })
          }
        />
      </Dialog>

      <Dialog
        open={dialog === "hold"}
        title={`Hold ${order.waybill_code} at the hub?`}
        onClose={() => setDialog(null)}
        actions={
          <>
            <Button variant="secondary" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button
              loading={hold.isPending}
              onClick={() =>
                hold.mutate({ orderId: order.id, reason: holdReason }, { onSuccess: () => setDialog(null) })
              }
            >
              Hold order
            </Button>
          </>
        }
      >
        <p className="mb-3">Automatic dispatch skips the order until you release it. The shop is informed.</p>
        <SelectField label="Reason" options={HOLD_REASONS} value={holdReason} onChange={(event) => setHoldReason(event.target.value)} />
      </Dialog>
    </div>
  );
}
