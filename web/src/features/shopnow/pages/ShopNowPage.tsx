// ShopNowPage - simulated partner storefront: create orders, follow status, webhook log

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { Alert, Badge, Button, Card, EmptyState, Loading, Pagination, Table, Td, Th } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { toast } from "@/lib/toast";
import { cancelOrder, listOrders, listWebhooks } from "../api";
import { CreateOrdersPanel } from "../components/CreateOrdersPanel";

const CANCELLABLE = new Set(["AWAITING_ASSIGNMENT", "ON_HOLD", "ASSIGNED"]);

function statusTone(status: string | null) {
  if (status === "DELIVERED") return "success" as const;
  if (status === "CANCELLED" || status === "RETURNED_TO_HUB") return "neutral" as const;
  if (status === "DELIVERY_FAILED") return "danger" as const;
  return "primary" as const;
}

export function ShopNowPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [webhookPage, setWebhookPage] = useState(1);

  const orders = useQuery({
    queryKey: ["shopnow", "orders", page],
    queryFn: () => listOrders(page),
    placeholderData: keepPreviousData,
  });
  const webhooks = useQuery({
    queryKey: ["shopnow", "webhooks", webhookPage],
    queryFn: () => listWebhooks(webhookPage),
    placeholderData: keepPreviousData,
  });

  const cancel = useMutation({
    mutationFn: cancelOrder,
    onSuccess: (order) => {
      toast.success(`Order ${order.waybill_code} cancelled.`);
      void queryClient.invalidateQueries({ queryKey: ["shopnow"] });
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  return (
    <div className="min-h-full bg-shop-50/40">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <span className="font-display text-xl font-extrabold text-shop-600">ShopNow</span>
          <span className="text-xs text-neutral-600">
            Simulated e-commerce partner of the{" "}
            <Link to="/" className="font-semibold text-primary-600">
              H4T Xpress
            </Link>{" "}
            demo
          </span>
        </div>
      </header>

      <main className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6">
        <Alert tone="warning" title="What is this page?">
          ShopNow plays the online shop. Orders created here are sent to H4T Xpress through the same partner
          API a real platform would use. Status updates arrive back as signed webhooks once dispatching starts.
        </Alert>

        <CreateOrdersPanel />

        <Card title="Orders sent to H4T Xpress">
          {orders.isPending && <Loading />}
          {orders.isError && <Alert tone="danger">{errorMessage(orders.error)}</Alert>}
          {orders.data && orders.data.items.length === 0 && <EmptyState title="No orders yet" />}
          {orders.data && orders.data.items.length > 0 && (
            <>
              <Table>
                <thead>
                  <tr>
                    <Th>Waybill</Th>
                    <Th>Recipient</Th>
                    <Th>Hub</Th>
                    <Th>Promised</Th>
                    <Th>Status (as ShopNow knows it)</Th>
                    <Th className="text-right">Actions</Th>
                  </tr>
                </thead>
                <tbody>
                  {orders.data.items.map((order) => (
                    <tr key={order.waybill_code}>
                      <Td className="font-mono text-xs">
                        {order.waybill_code}
                        {order.priority === "EXPRESS" && (
                          <span className="ml-2">
                            <Badge tone="warning">Express</Badge>
                          </span>
                        )}
                      </Td>
                      <Td>
                        <span className="block">{order.recipient_name}</span>
                        <span className="text-xs text-neutral-600">{order.delivery_address}</span>
                      </Td>
                      <Td>{order.hub_code}</Td>
                      <Td>{formatDateTime(order.promised_at)}</Td>
                      <Td>
                        <Badge tone={statusTone(order.last_status)}>{order.last_status ?? "Unknown"}</Badge>
                      </Td>
                      <Td className="text-right">
                        {CANCELLABLE.has(order.last_status ?? "") && (
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={cancel.isPending}
                            onClick={() => cancel.mutate(order.waybill_code)}
                          >
                            Cancel
                          </Button>
                        )}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
              <Pagination page={orders.data.page} pageSize={orders.data.page_size} total={orders.data.total} onChange={setPage} />
            </>
          )}
        </Card>

        <Card title="Webhooks received from H4T Xpress">
          {webhooks.data && webhooks.data.items.length === 0 && (
            <EmptyState title="No webhooks yet">
              H4T sends a signed webhook for every important change (driver assigned, ETA changed, delivered).
            </EmptyState>
          )}
          {webhooks.data && webhooks.data.items.length > 0 && (
            <>
              <Table>
                <thead>
                  <tr>
                    <Th>Received</Th>
                    <Th>Event</Th>
                    <Th>Waybill</Th>
                    <Th>Signature</Th>
                  </tr>
                </thead>
                <tbody>
                  {webhooks.data.items.map((hook) => (
                    <tr key={hook.id}>
                      <Td>{formatDateTime(hook.received_at)}</Td>
                      <Td className="font-mono text-xs">{hook.event_type}</Td>
                      <Td className="font-mono text-xs">{hook.waybill_code ?? "-"}</Td>
                      <Td>
                        <Badge tone={hook.signature_valid ? "success" : "danger"}>
                          {hook.signature_valid ? "Valid" : "Invalid"}
                        </Badge>
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
              <Pagination
                page={webhooks.data.page}
                pageSize={webhooks.data.page_size}
                total={webhooks.data.total}
                onChange={setWebhookPage}
              />
            </>
          )}
        </Card>
      </main>
    </div>
  );
}
