// OrderPanel - right column of H-03: status timeline, delivery data, attempts and the
// manual actions available in the order's current status.

import { useState } from "react";
import { Link } from "react-router";
import { CandidatePicker } from "@/components/CandidatePicker";
import { OrderStatusBadge } from "@/components/StatusBadge";
import { Timeline } from "@/components/Timeline";
import { Alert, Badge, Button, Card, Dialog, SelectField } from "@/components/ui";
import { formatDateTime, formatMoney, formatPhone } from "@/lib/format";
import { FAILURE_REASON } from "@/lib/labels";
import { hasPermission, useSession } from "@/lib/session";
import type { HubOrderDetail } from "@/types";
import { useConfirmReturned, useHold, useOrderCandidates, useReassign, useReleaseHold } from "../hooks";

const HOLD_REASONS = ["Address needs checking", "Customer asked to wait", "Parcel needs repacking", "No driver available"].map(
  (value) => ({ value, label: value }),
);
const REASSIGNABLE = new Set(["AWAITING_ASSIGNMENT", "ASSIGNED", "ON_HOLD"]);

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

  const incidentOpen = Boolean(order.incident_id);
  const pickup = { lat: order.hub_lat, lng: order.hub_lng, label: "Pickup at the hub", kind: "hub" as const };

  return (
    <div className="flex flex-col gap-4">
      <Card title="Status" actions={<OrderStatusBadge status={order.status} />}>
        {order.at_risk && (
          <Alert tone="danger" className="mb-4">
            SLA risk: ETA {formatDateTime(order.current_eta)} is after the promised {formatDateTime(order.promised_at)}.
          </Alert>
        )}
        {incidentOpen && (
          <Alert tone="warning" className="mb-4">
            This order is part of an open incident.{" "}
            <Link to={`/hub/incidents/${order.incident_id}`} className="font-semibold underline">
              Handle it there
            </Link>
            .
          </Alert>
        )}
        <Timeline events={order.timeline} />
      </Card>

      {canAct && !incidentOpen && (
        <Card title="Actions">
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
        </Card>
      )}

      <Card title="Delivery">
        <dl className="flex flex-col gap-2 text-sm">
          <div className="flex justify-between gap-3">
            <dt className="text-neutral-500">Customer</dt>
            <dd className="text-right">
              {order.recipient_name}
              <span className="block text-xs text-neutral-600">{formatPhone(order.recipient_phone)}</span>
            </dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-neutral-500">Address</dt>
            <dd className="text-right">{order.delivery_address}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-neutral-500">Driver</dt>
            <dd className="text-right">
              {order.driver ? order.driver.name : "Not assigned"}
              {order.driver?.phone && <span className="block text-xs text-neutral-600">{formatPhone(order.driver.phone)}</span>}
              {order.handover_from && <span className="block text-xs text-warning-700">Hand-over from {order.handover_from}</span>}
            </dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-neutral-500">Promised / ETA</dt>
            <dd className="text-right">
              {formatDateTime(order.promised_at)}
              <span className="block text-xs text-neutral-600">
                ETA {formatDateTime(order.current_eta)}
                {order.eta_is_estimate ? " (estimate)" : ""}
              </span>
            </dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-neutral-500">Parcel</dt>
            <dd className="text-right">
              {order.items.map((item) => `${item.name} x${item.qty}`).join(", ")}
              <span className="block text-xs text-neutral-600">
                {Number(order.weight_kg)} kg - COD {formatMoney(order.cod_amount)}
              </span>
            </dd>
          </div>
          {order.priority === "EXPRESS" && (
            <div>
              <Badge tone="danger">Express</Badge>
            </div>
          )}
        </dl>
      </Card>

      {order.attempts.length > 0 && (
        <Card title="Delivery attempts">
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
                      <img src={url} alt="Proof of delivery" className="size-16 rounded-input border border-line object-cover" />
                    </a>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </Card>
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
