// OrdersTable - the hub's order board (UC-02), drawn as the Figma "Latest Shipping" card:
// status filter, SLA risk first, search from the top bar (?q=), link to tracking

import { X } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router";
import { OrderStatusBadge } from "@/components/StatusBadge";
import { Alert, Badge, EmptyState, Loading, Pagination, Panel, Table, Td, Th } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatClock, formatDateTime } from "@/lib/format";
import { ORDER_STATUS } from "@/lib/labels";
import type { OrderStatus } from "@/types";
import type { OrderFilters } from "../api";
import { useHubOrders } from "../hooks";

const STATUS_OPTIONS = Object.entries(ORDER_STATUS).map(([value, { label }]) => ({ value, label }));

const CONTROL = "h-9 rounded-lg border border-line bg-white px-3 text-sm text-neutral-700 focus:border-primary-500 focus:outline-none";

export function OrdersTable({
  query,
  atRisk = false,
  pageSize = 8,
  className,
}: {
  /** Search text from the top bar; the board is re-created when it changes. */
  query?: string;
  atRisk?: boolean;
  pageSize?: number;
  className?: string;
}) {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<OrderFilters>({
    page: 1,
    page_size: pageSize,
    q: query || undefined,
    at_risk: atRisk || undefined,
  });
  const orders = useHubOrders(filters);

  const update = (patch: Partial<OrderFilters>) => setFilters((current) => ({ ...current, ...patch, page: 1 }));

  const controls = (
    <div className="flex flex-wrap items-center gap-2">
      {filters.q && (
        <button
          type="button"
          className="flex h-9 items-center gap-1.5 rounded-lg bg-primary-50 px-3 text-sm text-primary-700"
          onClick={() => {
            update({ q: undefined });
            navigate("/hub", { replace: true });
          }}
        >
          Search: {filters.q}
          <X className="size-3.5" aria-label="Clear search" />
        </button>
      )}
      <select
        aria-label="Status"
        className={CONTROL}
        value={filters.status ?? ""}
        onChange={(event) => update({ status: (event.target.value || undefined) as OrderStatus | undefined })}
      >
        <option value="">All statuses</option>
        {STATUS_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <label className={`${CONTROL} flex items-center gap-2`}>
        <input
          type="checkbox"
          className="size-4 accent-danger-500"
          checked={Boolean(filters.at_risk)}
          onChange={(event) => update({ at_risk: event.target.checked || undefined })}
        />
        SLA risk only
      </label>
    </div>
  );

  return (
    <Panel title="Latest orders" action={controls} className={className} bodyClassName="p-0">
      {orders.isError && <Alert tone="danger" className="m-5">{errorMessage(orders.error)}</Alert>}
      {orders.isPending && <Loading />}
      {orders.data?.items.length === 0 && (
        <div className="p-5">
          <EmptyState title="No orders match these filters" />
        </div>
      )}
      {orders.data && orders.data.items.length > 0 && (
        <>
          <div className="px-3">
            <Table framed={false}>
              <thead>
                <tr>
                  <Th>Order ID</Th>
                  <Th>Status</Th>
                  <Th>Customer</Th>
                  <Th>Driver</Th>
                  <Th>Promised</Th>
                  <Th className="text-right">ETA</Th>
                </tr>
              </thead>
              <tbody>
                {orders.data.items.map((order) => (
                  <tr
                    key={order.id}
                    onClick={() => navigate(`/hub/tracking/${order.id}`)}
                    className={order.at_risk ? "cursor-pointer bg-danger-50/40 hover:bg-danger-50" : "cursor-pointer hover:bg-neutral-50"}
                  >
                    <Td>
                      <p className="font-medium text-ink">{order.waybill_code}</p>
                      {(order.priority === "EXPRESS" || order.has_incident) && (
                        <div className="mt-1 flex gap-1">
                          {order.priority === "EXPRESS" && <Badge tone="danger">Express</Badge>}
                          {order.has_incident && <Badge tone="warning">Incident</Badge>}
                        </div>
                      )}
                    </Td>
                    <Td>
                      <OrderStatusBadge status={order.status} />
                    </Td>
                    <Td>
                      <p>{order.recipient_name}</p>
                      <p className="max-w-56 truncate text-xs text-neutral-500">{order.delivery_address}</p>
                    </Td>
                    <Td>{order.driver_name ?? <span className="text-neutral-400">Not assigned</span>}</Td>
                    <Td>{formatDateTime(order.promised_at)}</Td>
                    <Td className={order.at_risk ? "text-right font-semibold text-danger-700" : "text-right"}>
                      {formatClock(order.current_eta)}
                      {order.at_risk && <span className="block text-xs">SLA risk</span>}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
          <div className="px-5 pb-4">
            <Pagination
              page={filters.page}
              pageSize={filters.page_size}
              total={orders.data.total}
              onChange={(page) => setFilters((current) => ({ ...current, page }))}
            />
          </div>
        </>
      )}
    </Panel>
  );
}
