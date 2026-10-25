// StopPage - D-08 (Figma "Order Details"): customer card, the parcels for this stop and
// "Mark as undelivered" with notes and the next delivery date.

import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { ScreenTitle } from "@/components/ScreenTitle";
import { OrderStatusBadge } from "@/components/StatusBadge";
import { Alert, Badge, Button, Card, EmptyState, Loading, Switch } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatClock, formatMoney, formatPhone } from "@/lib/format";
import { toast } from "@/lib/toast";
import type { DriverOrder } from "@/types";
import { FailForm, type FailValues } from "../components/FailForm";
import { ScanDialog } from "../components/ScanDialog";
import { useFailOrder, useRoute } from "../hooks";

function mapsLink(lat: number, lng: number): string {
  return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
}

export function StopPage() {
  const { stopId = "" } = useParams();
  const navigate = useNavigate();
  const route = useRoute();
  const fail = useFailOrder();
  const [undelivered, setUndelivered] = useState(false);
  const [scanning, setScanning] = useState<DriverOrder | null>(null);

  if (route.isPending) return <Loading />;
  if (route.isError) return <Alert tone="danger">{errorMessage(route.error)}</Alert>;

  const stop = route.data.stops.find((item) => item.id === stopId);
  if (!stop) {
    return (
      <>
        <ScreenTitle title="Order Details" back="/driver/route" />
        <EmptyState title="This stop is finished">
          <Link to="/driver/route" className="font-semibold text-primary-600">
            Back to the route
          </Link>
        </EmptyState>
      </>
    );
  }

  const onTheRoad = stop.orders.filter((order) => order.status === "OUT_FOR_DELIVERY");
  const codTotal = stop.orders.reduce((sum, order) => sum + Number(order.cod_amount), 0);

  async function failAll(values: FailValues) {
    try {
      for (const order of onTheRoad) {
        await fail.mutateAsync({ orderId: order.id, data: values });
      }
    } catch {
      return; // shown by the form through `fail.error`
    }
    toast.success(values.proposed_date ? "Delivery rescheduled." : "Parcels will go back to the hub.");
    navigate(`/driver/orders/${onTheRoad[0].id}/done?result=failed`);
  }

  return (
    <div className="flex flex-col gap-4">
      <ScreenTitle title="Order Details" back="/driver/route" />

      <Card>
        <div className="flex items-start justify-between gap-3">
          <h2 className="font-display text-lg font-bold text-primary-700">{stop.recipient_name}</h2>
          <p className="text-sm font-semibold text-primary-700">ETA {formatClock(stop.eta)}</p>
        </div>
        <dl className="mt-3 flex flex-col gap-1.5 text-sm">
          <div className="flex justify-between gap-3">
            <dt className="text-neutral-500">Address</dt>
            <dd className="text-right">{stop.address}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-neutral-500">Parcels</dt>
            <dd>{stop.orders.length}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-neutral-500">Cash to collect</dt>
            <dd>{formatMoney(codTotal)}</dd>
          </div>
        </dl>
        <div className="mt-4 flex gap-4 border-t border-line pt-3 text-sm font-semibold">
          <a href={`tel:${stop.recipient_phone}`} className="text-primary-600">
            Call customer ({formatPhone(stop.recipient_phone)})
          </a>
          <a href={mapsLink(stop.lat, stop.lng)} target="_blank" rel="noreferrer" className="text-primary-600">
            Directions
          </a>
        </div>
      </Card>

      <section className="flex flex-col gap-3">
        <h2 className="text-base">Delivery requests ({String(stop.orders.length).padStart(2, "0")})</h2>
        {stop.orders.map((order) => (
          <Card key={order.id} className="p-4">
            <div className="flex items-center justify-between gap-2">
              <p className="font-display font-bold">{order.waybill_code}</p>
              {order.status === "ASSIGNED" ? (
                <Button size="sm" onClick={() => setScanning(order)}>
                  Scan
                </Button>
              ) : (
                <OrderStatusBadge status={order.status} />
              )}
            </div>
            <p className="mt-2 text-sm">{order.items.map((item) => item.name).join(", ")}</p>
            <p className="text-sm font-semibold text-primary-700">
              Qty: {order.items.reduce((sum, item) => sum + item.qty, 0)} | COD: {formatMoney(order.cod_amount)}
            </p>
            {order.note && <p className="mt-1 text-xs text-neutral-600">Note: {order.note}</p>}
            {order.priority === "EXPRESS" && (
              <div className="mt-2">
                <Badge tone="danger">Express</Badge>
              </div>
            )}
            {order.status === "OUT_FOR_DELIVERY" && (
              <div className="mt-3 flex gap-2">
                <Link
                  to={`/driver/orders/${order.id}`}
                  className="inline-flex h-9 flex-1 items-center justify-center rounded-button bg-primary-600 text-sm font-semibold text-white"
                >
                  Deliver
                </Link>
                <Link
                  to={`/driver/orders/${order.id}/eta`}
                  className="inline-flex h-9 flex-1 items-center justify-center rounded-button border border-line text-sm font-semibold"
                >
                  Update ETA
                </Link>
              </div>
            )}
          </Card>
        ))}
      </section>

      {onTheRoad.length > 0 && (
        <>
          <div className="flex items-center justify-between">
            <span className="text-sm">Mark as undelivered</span>
            <Switch label="Mark as undelivered" checked={undelivered} onChange={setUndelivered} />
          </div>
          {undelivered && (
            <Card>
              <FailForm submitting={fail.isPending} error={fail.error} onSubmit={(values) => void failAll(values)} />
            </Card>
          )}
        </>
      )}

      <Link
        to={`/driver/incidents/new?order=${stop.orders[0].id}`}
        className="text-center text-sm font-semibold text-danger-700"
      >
        Report an issue on the way
      </Link>
      <ScanDialog order={scanning} onClose={() => setScanning(null)} />
    </div>
  );
}
