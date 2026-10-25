// OrdersTable - the hub's order board (UC-02): filters, SLA risk first, link to tracking

import { useState } from "react";
import { useNavigate } from "react-router";
import { OrderStatusBadge } from "@/components/StatusBadge";
import { Alert, Badge, Button, EmptyState, Loading, Pagination, SelectField, Table, Td, TextField, Th } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatClock, formatDateTime } from "@/lib/format";
import { ORDER_STATUS } from "@/lib/labels";
import type { OrderStatus } from "@/types";
import type { OrderFilters } from "../api";
import { useHubOrders } from "../hooks";

const STATUS_OPTIONS = Object.entries(ORDER_STATUS).map(([value, { label }]) => ({ value, label }));

export function OrdersTable({ pageSize = 10 }: { pageSize?: number }) {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<OrderFilters>({ page: 1, page_size: pageSize });
  const [search, setSearch] = useState("");
  const orders = useHubOrders(filters);

  const update = (patch: Partial<OrderFilters>) => setFilters((current) => ({ ...current, ...patch, page: 1 }));

  return (
    <div className="flex flex-col gap-3">
      <form
        className="grid gap-3 md:grid-cols-[2fr_1fr_auto_auto]"
        onSubmit={(event) => {
          event.preventDefault();
          update({ q: search.trim() || undefined });
        }}
      >
        <TextField
          compact
          aria-label="Search orders"
          placeholder="Search waybill, customer name or phone"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <SelectField
          compact
          aria-label="Status"
          placeholder="All statuses"
          options={STATUS_OPTIONS}
          value={filters.status ?? ""}
          onChange={(event) => update({ status: (event.target.value || undefined) as OrderStatus | undefined })}
        />
        <label className="flex h-10 items-center gap-2 rounded-input border border-line bg-white px-3 text-sm">
          <input
            type="checkbox"
            className="size-4 accent-danger-500"
            checked={Boolean(filters.at_risk)}
            onChange={(event) => update({ at_risk: event.target.checked || undefined })}
          />
          SLA risk only
        </label>
        <Button type="submit" variant="secondary">
          Search
        </Button>
      </form>

      {orders.isError && <Alert tone="danger">{errorMessage(orders.error)}</Alert>}
      {orders.isPending && <Loading />}
      {orders.data?.items.length === 0 && <EmptyState title="No orders match these filters" />}
      {orders.data && orders.data.items.length > 0 && (
        <>
          <Table>
            <thead>
              <tr>
                <Th>Order</Th>
                <Th>Status</Th>
                <Th>Customer</Th>
                <Th>Driver</Th>
                <Th>Promised</Th>
                <Th>ETA</Th>
              </tr>
            </thead>
            <tbody>
              {orders.data.items.map((order) => (
                <tr
                  key={order.id}
                  onClick={() => navigate(`/hub/tracking/${order.id}`)}
                  className={order.at_risk ? "cursor-pointer bg-danger-50/50 hover:bg-danger-50" : "cursor-pointer hover:bg-neutral-50"}
                >
                  <Td>
                    <p className="font-semibold">{order.waybill_code}</p>
                    <div className="mt-1 flex gap-1">
                      {order.priority === "EXPRESS" && <Badge tone="danger">Express</Badge>}
                      {order.has_incident && <Badge tone="warning">Incident</Badge>}
                    </div>
                  </Td>
                  <Td>
                    <OrderStatusBadge status={order.status} />
                  </Td>
                  <Td>
                    <p>{order.recipient_name}</p>
                    <p className="max-w-56 truncate text-xs text-neutral-600">{order.delivery_address}</p>
                  </Td>
                  <Td>{order.driver_name ?? <span className="text-neutral-400">Not assigned</span>}</Td>
                  <Td>{formatDateTime(order.promised_at)}</Td>
                  <Td className={order.at_risk ? "font-semibold text-danger-700" : undefined}>
                    {formatClock(order.current_eta)}
                    {order.at_risk && <span className="block text-xs">SLA risk</span>}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
          <Pagination
            page={filters.page}
            pageSize={filters.page_size}
            total={orders.data.total}
            onChange={(page) => setFilters((current) => ({ ...current, page }))}
          />
        </>
      )}
    </div>
  );
}
