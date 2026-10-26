// Status badges - order status, incident status and priority with consistent colours

import { Badge } from "@/components/ui";
import { INCIDENT_STATUS, ORDER_STATUS, PRIORITY } from "@/lib/labels";
import type { IncidentPriority, IncidentStatus, OrderStatus } from "@/types";

export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  const { label, tone } = ORDER_STATUS[status];
  return <Badge tone={tone}>{label}</Badge>;
}

export function IncidentStatusBadge({ status }: { status: IncidentStatus }) {
  const { label, tone } = INCIDENT_STATUS[status];
  return <Badge tone={tone}>{label}</Badge>;
}

export function PriorityBadge({ priority }: { priority: IncidentPriority | null }) {
  if (!priority) return <Badge tone="neutral">Not classified</Badge>;
  const { label, tone } = PRIORITY[priority];
  return <Badge tone={tone}>{label} priority</Badge>;
}
