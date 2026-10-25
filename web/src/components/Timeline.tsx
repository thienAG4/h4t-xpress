// Timeline - order history for the hub (H-03) and the four delivery steps for drivers (D-07)

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

/** Full event list, newest last, as stored in order_events. */
export function Timeline({ events }: { events: TimelineEvent[] }) {
  return (
    <ol className="relative flex flex-col gap-4 border-l border-line pl-5">
      {events.map((event, index) => {
        const { title, detail } = describe(event);
        const last = index === events.length - 1;
        return (
          <li key={`${event.at}-${index}`} className="relative">
            <span
              className={cn(
                "absolute top-1.5 -left-[25px] size-2.5 rounded-full border-2",
                last ? "border-primary-600 bg-primary-600" : "border-primary-200 bg-white",
              )}
            />
            <p className={cn("text-sm", last ? "font-semibold text-ink" : "text-neutral-700")}>{title}</p>
            <p className="text-xs text-warning-700">{formatDateTime(event.at)}</p>
            {detail && <p className="mt-0.5 text-xs text-neutral-600">{detail}</p>}
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
