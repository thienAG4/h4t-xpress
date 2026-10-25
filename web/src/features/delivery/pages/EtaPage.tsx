// EtaPage - D-12 (Figma "Tài xế cập nhật ETA"): map, customer card, new time and reason,
// then the "Successful" sheet. The partner and the customer get the new time by webhook.

import { useState } from "react";
import { Link, useParams } from "react-router";
import { MapView, type MapPoint } from "@/components/MapView";
import { ScreenTitle } from "@/components/ScreenTitle";
import { Alert, Button, Card, Loading, SelectField, TextField } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatClock, formatDateTime, formatMoney, fromLocalInput, toLocalInput } from "@/lib/format";
import { useDriverOrder, useRoute, useUpdateEta } from "../hooks";

const REASONS = [
  "Heavy traffic",
  "Bad weather",
  "Customer asked for a later time",
  "Previous stop took longer",
  "Vehicle problem",
].map((value) => ({ value, label: value }));

export function EtaPage() {
  const { orderId = "" } = useParams();
  const order = useDriverOrder(orderId);
  const route = useRoute();
  const update = useUpdateEta();
  const [eta, setEta] = useState(() => toLocalInput(new Date(Date.now() + 60 * 60_000)));
  const [reason, setReason] = useState("");
  const [savedEta, setSavedEta] = useState<string | null>(null);

  if (order.isPending) return <Loading />;
  if (order.isError) return <Alert tone="danger">{errorMessage(order.error)}</Alert>;
  const data = order.data;

  const points: MapPoint[] = [
    { id: "to", lat: data.delivery_lat, lng: data.delivery_lng, label: data.recipient_name, kind: "stop" },
  ];
  const driver = route.data;
  if (driver?.driver_lat != null && driver.driver_lng != null) {
    points.push({ id: "me", lat: driver.driver_lat, lng: driver.driver_lng, label: "You are here", kind: "driver" });
  }

  if (savedEta) {
    return (
      <div className="flex flex-col gap-4">
        <ScreenTitle title="Update ETA" back={`/driver/orders/${orderId}`} />
        <MapView points={points} className="h-56" />
        <Card className="text-center">
          <p className="font-display text-lg font-bold">Successful</p>
          <p className="mx-auto mt-3 flex size-14 items-center justify-center rounded-full bg-primary-600 font-display text-lg font-bold text-white">
            OK
          </p>
          <p className="mt-3 text-sm text-neutral-600">
            You have successfully updated the ETA to {formatClock(savedEta)}. The customer has been informed.
          </p>
          <Link
            to={`/driver/orders/${orderId}`}
            className="mt-4 inline-flex h-10 w-full items-center justify-center rounded-button border border-line font-semibold text-primary-600"
          >
            View details
          </Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <ScreenTitle title="Update ETA" back={`/driver/orders/${orderId}`} />
      <MapView points={points} className="h-56" />

      <Card>
        <p className="font-semibold">{data.recipient_name}</p>
        <p className="text-xs text-neutral-500">{data.waybill_code}</p>
        <dl className="mt-3 flex flex-col gap-1.5 text-sm">
          <div className="flex justify-between gap-3">
            <dt className="text-neutral-500">Deliver to</dt>
            <dd className="text-right">{data.delivery_address}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-neutral-500">Current ETA</dt>
            <dd>
              {formatDateTime(data.current_eta)}
              {data.eta_is_estimate ? " (estimate)" : ""}
            </dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-neutral-500">Promised by</dt>
            <dd>{formatDateTime(data.promised_at)}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-neutral-500">Cash on delivery</dt>
            <dd>{formatMoney(data.cod_amount)}</dd>
          </div>
        </dl>
      </Card>

      <form
        className="flex flex-col gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          const value = fromLocalInput(eta);
          update.mutate({ orderId, data: { eta: value, reason } }, { onSuccess: () => setSavedEta(value) });
        }}
      >
        <TextField
          type="datetime-local"
          label="New delivery time"
          value={eta}
          min={toLocalInput(new Date())}
          onChange={(event) => setEta(event.target.value)}
          required
        />
        <SelectField
          label="Reason (shared with the customer)"
          placeholder="Choose a reason"
          options={REASONS}
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          required
        />
        {update.isError && <Alert tone="danger">{errorMessage(update.error)}</Alert>}
        <div className="grid grid-cols-2 gap-3">
          <Link
            to={`/driver/orders/${orderId}`}
            className="inline-flex h-[50px] items-center justify-center rounded-button border border-primary-600 font-display font-bold text-primary-600"
          >
            Cancel
          </Link>
          <Button type="submit" size="lg" loading={update.isPending} disabled={!reason}>
            Update
          </Button>
        </div>
      </form>
    </div>
  );
}
