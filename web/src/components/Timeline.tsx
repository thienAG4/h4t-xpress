// Timeline - order history for the hub (H-03) and the four delivery steps for drivers (D-07)

import { Calendar, Package } from "lucide-react";
import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";
import { FAILURE_REASON, INCIDENT_TYPE, ORDER_STATUS } from "@/lib/labels";
import type { FailureReason, IncidentType, OrderStatus, TimelineEvent } from "@/types";

function describe(event: TimelineEvent): { title: string; detail?: string } {
  const payload = event.payload as Record<string, unknown>;
  const reason = typeof payload.reason === "string" ? payload.reason : undefined;
  if (event.type === "ETA_CHANGED") {
    const eta = typeof payload.eta === "string" ? formatDateTime(payload.eta) : undefined;
    return { title: "Delivery time changed", detail: [eta && `New ETA ${eta}`, reason].filter(Boolean).join(" - ") };
  }
  if (event.type === "INCIDENT") {
    const kind = typeof payload.type === "string" ? INCIDENT_TYPE[payload.type as IncidentType] : undefined;
    return { title: "Incident reported", detail: kind ?? reason };
  }
  if (event.type === "NOTE") return { title: "Note", detail: reason };
  const title = event.to_status ? ORDER_STATUS[event.to_status].label : "Updated";
  const detail = reason && reason in FAILURE_REASON ? FAILURE_REASON[reason as FailureReason] : reason;
  return { title, detail };
}

/**
 * Full event list, newest last, as stored in order_events. Drawn like the Figma "Status" card:
 * markers on a dashed line, the date at the right, the first and the latest event boxed.
 */
export function Timeline({ events }: { events: TimelineEvent[] }) {
  return (
    <ol className="flex flex-col">
      {events.map((event, index) => {
        const { title, detail } = describe(event);
        const first = index === 0;
        const last = index === events.length - 1;
        const boxed = first || last;
        return (
          <li key={`${event.at}-${index}`} className="flex gap-3">
            <div className="flex w-5 shrink-0 flex-col items-center">
              {boxed ? (
                <Package
                  className={cn("mt-3 size-[18px] shrink-0", last ? "text-primary-600" : "text-neutral-500")}
                  strokeWidth={1.75}
                  aria-hidden
                />
              ) : (
                <span className="mt-1.5 size-2.5 shrink-0 rounded-full border-2 border-primary-600 bg-white" aria-hidden />
              )}
              {!last && <span className="mt-1 w-px flex-1 border-l border-dashed border-primary-300" aria-hidden />}
            </div>
            <div className={cn("mb-3 min-w-0 flex-1", boxed && "rounded-md border border-line px-3 py-2.5")}>
              <div className="flex items-start justify-between gap-3">
                <p className={cn("text-sm", last ? "font-semibold text-ink" : "text-ink")}>{title}</p>
                <p className="flex shrink-0 items-center gap-1 text-xs text-neutral-600 tabular-nums">
                  <Calendar className="size-3.5" aria-hidden />
                  {formatDateTime(event.at)}
                </p>
              </div>
              {detail && <p className="mt-1 text-sm text-neutral-600">{detail}</p>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

const STEPS: { status: OrderStatus; label: string }[] = [
  { status: "ASSIGNED", label: "Driver en route to pickup" },
  { status: "PICKED_UP", label: "Package picked up" },
  { status: "OUT_FOR_DELIVERY", label: "Out for delivery" },
  { status: "DELIVERED", label: "Delivered" },
];
const ORDER = STEPS.map((step) => step.status);

const FAILED: OrderStatus[] = ["DELIVERY_FAILED", "RESCHEDULED", "RETURNING", "RETURNED_TO_HUB"];

/** The Figma "Package Status" list: square markers, done steps filled, times in orange. */
export function DeliverySteps({ status, events }: { status: OrderStatus; events: TimelineEvent[] }) {
  const failed = FAILED.includes(status);
  const position = failed ? ORDER.length - 1 : ORDER.indexOf(status);
  const timeOf = (target: OrderStatus) =>
    [...events].reverse().find((event) => event.to_status === target)?.at ?? null;

  return (
    <ol className="flex flex-col">
      {STEPS.map((step, index) => {
        const last = index === STEPS.length - 1;
        const label = last && failed ? ORDER_STATUS[status].label : step.label;
        const at = timeOf(last && failed ? "DELIVERY_FAILED" : step.status);
        const done = index <= position;
        return (
          <li key={step.status} className="flex gap-3">
            <div className="flex flex-col items-center">
              <span
                className={cn(
                  "mt-1 size-3.5 rounded-[3px] border-2",
                  done ? "border-primary-600 bg-primary-600" : "border-neutral-300 bg-white",
                  last && failed && "border-danger-500 bg-danger-500",
                )}
              />
              {!last && <span className="w-px flex-1 bg-neutral-300" />}
            </div>
            <div className="pb-3">
              <p className={cn("text-sm", index === position ? "font-semibold text-primary-600" : "text-neutral-600")}>
                {label}
              </p>
              <p className={cn("text-xs", at ? "text-warning-700" : "text-neutral-400")}>
                {at ? formatDateTime(at) : "Pending"}
              </p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
