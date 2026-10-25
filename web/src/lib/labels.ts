// Labels and badge tones - one place for the words shown for statuses, types and reasons

import type {
  FailureReason,
  IncidentCategory,
  IncidentPriority,
  IncidentStatus,
  IncidentType,
  OrderStatus,
  ResolutionSolution,
} from "@/types";

export type Tone = "info" | "success" | "warning" | "danger" | "neutral" | "primary";

export const ORDER_STATUS: Record<OrderStatus, { label: string; tone: Tone }> = {
  AWAITING_ASSIGNMENT: { label: "Waiting for driver", tone: "warning" },
  ON_HOLD: { label: "On hold", tone: "danger" },
  ASSIGNED: { label: "Assigned", tone: "primary" },
  PICKED_UP: { label: "Picked up", tone: "primary" },
  OUT_FOR_DELIVERY: { label: "Out for delivery", tone: "info" },
  DELIVERED: { label: "Delivered", tone: "success" },
  DELIVERY_FAILED: { label: "Delivery failed", tone: "danger" },
  RESCHEDULED: { label: "Rescheduled", tone: "warning" },
  RETURNING: { label: "Returning", tone: "warning" },
  RETURNED_TO_HUB: { label: "Returned to hub", tone: "neutral" },
  CANCELLED: { label: "Cancelled", tone: "neutral" },
};

export const INCIDENT_STATUS: Record<IncidentStatus, { label: string; tone: Tone }> = {
  OPEN: { label: "New", tone: "danger" },
  IN_REVIEW: { label: "In review", tone: "warning" },
  RESOLVING: { label: "Resolving", tone: "primary" },
  RESOLVED: { label: "Resolved", tone: "success" },
  CLOSED_NO_ACTION: { label: "Closed", tone: "neutral" },
};

export const INCIDENT_TYPE: Record<IncidentType, string> = {
  TRAFFIC_JAM: "Traffic jam",
  WEATHER: "Bad weather",
  TRAFFIC_ACCIDENT: "Traffic accident",
  VEHICLE_BREAKDOWN: "Vehicle breakdown",
  HEALTH: "Health problem",
  GOODS_DAMAGED: "Damaged goods",
  OTHER: "Other",
  ETA_ANOMALY: "ETA keeps slipping",
  DRIVER_IDLE: "Driver not moving",
};

/** Types a driver can choose in the report form (the last two are raised by the system). */
export const REPORTABLE_TYPES: IncidentType[] = [
  "TRAFFIC_JAM",
  "WEATHER",
  "TRAFFIC_ACCIDENT",
  "VEHICLE_BREAKDOWN",
  "HEALTH",
  "GOODS_DAMAGED",
  "OTHER",
];

export const CATEGORY: Record<IncidentCategory, { label: string; hint: string }> = {
  OBJECTIVE: { label: "Objective", hint: "Road or weather: the driver can continue on another route." },
  SUBJECTIVE: { label: "Subjective", hint: "Driver or vehicle: another driver should take over." },
};

export const PRIORITY: Record<IncidentPriority, { label: string; tone: Tone }> = {
  HIGH: { label: "High", tone: "danger" },
  MEDIUM: { label: "Medium", tone: "warning" },
  LOW: { label: "Low", tone: "neutral" },
};

export const SOLUTION: Record<ResolutionSolution, { label: string; hint: string }> = {
  ROUTE_SUGGESTED: { label: "New route", hint: "The same driver continues with a new stop order." },
  DRIVER_REASSIGNMENT: { label: "Driver reassignment", hint: "Another driver collects the parcels." },
  HOLD_AT_HUB: { label: "Hold at hub", hint: "Parcels go back to the hub for a later delivery." },
};

export const FAILURE_REASON: Record<FailureReason, string> = {
  CUSTOMER_ABSENT: "Customer not at home",
  CUSTOMER_UNREACHABLE: "Cannot reach the customer",
  CUSTOMER_REFUSED: "Customer refused the parcel",
  WRONG_ADDRESS: "Wrong address",
  OTHER: "Other reason",
};

export function options<T extends string>(labels: Record<T, string | { label: string }>) {
  return (Object.entries(labels) as [T, string | { label: string }][]).map(([value, label]) => ({
    value,
    label: typeof label === "string" ? label : label.label,
  }));
}
