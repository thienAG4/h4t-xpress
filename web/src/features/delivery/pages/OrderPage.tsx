// OrderPage - D-10 (Figma "Package Delivered") with proof of delivery (D-13):
// package information, cash to collect, photo, then "Delivery failed" or "Successful".

import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { PhotoPicker } from "@/components/PhotoPicker";
import { ScreenTitle } from "@/components/ScreenTitle";
import { DeliverySteps } from "@/components/Timeline";
import { Alert, Button, Card, Dialog, Loading, TextAreaField } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatDateTime, formatMoney, formatPhone } from "@/lib/format";
import type { UploadedFile } from "@/types";
import { FailForm } from "../components/FailForm";
import { useDeliverOrder, useDriverOrder, useFailOrder, useRoute } from "../hooks";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 text-sm">
      <dt className="text-neutral-500">{label}</dt>
      <dd className="text-right text-warning-700">{value}</dd>
    </div>
  );
}

export function OrderPage() {
  const { orderId = "" } = useParams();
  const navigate = useNavigate();
  const order = useDriverOrder(orderId);
  const route = useRoute();
  const deliver = useDeliverOrder();
  const fail = useFailOrder();
  const [photos, setPhotos] = useState<UploadedFile[]>([]);
  const [note, setNote] = useState("");
  const [photoError, setPhotoError] = useState<string>();
  const [failing, setFailing] = useState(false);

  if (order.isPending) return <Loading />;
  if (order.isError) return <Alert tone="danger">{errorMessage(order.error)}</Alert>;

  const data = order.data;
  const back = data.stop_id ? `/driver/stops/${data.stop_id}` : "/driver/route";
  const onTheRoad = data.status === "OUT_FOR_DELIVERY";
  const items = data.items.map((item) => `${item.name} x${item.qty}`).join(", ");

  return (
    <div className="flex flex-col gap-4">
      <ScreenTitle title="Package Delivered" back={back} />

      <Card title="Package information">
        <dl className="flex flex-col gap-3">
          <div>
            <dt className="text-sm font-semibold">Origin details</dt>
            <dd className="text-sm text-neutral-600">
              {data.handover_from ? `Hand-over from ${data.handover_from}` : (route.data?.hub_name ?? "H4T hub")}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-semibold">Destination details</dt>
            <dd className="text-sm text-neutral-600">
              {data.recipient_name}, {data.delivery_address}
            </dd>
            <dd className="text-sm text-neutral-600">{formatPhone(data.recipient_phone)}</dd>
          </div>
          <div className="flex flex-col gap-1">
            <dt className="text-sm font-semibold">Other details</dt>
            <Row label="Package items" value={items} />
            <Row label="Weight of items" value={`${Number(data.weight_kg)} kg`} />
            <Row label="Tracking number" value={data.waybill_code} />
            <Row label="Promised by" value={formatDateTime(data.promised_at)} />
          </div>
        </dl>
      </Card>

      <Card title="Charges">
        <dl className="flex flex-col gap-1">
          <Row label="Cash on delivery" value={formatMoney(data.cod_amount)} />
          <div className="mt-1 flex justify-between border-t border-line pt-2 text-sm font-semibold">
            <dt>Collect from customer</dt>
            <dd className="text-warning-700">{formatMoney(data.cod_amount)}</dd>
          </div>
        </dl>
      </Card>

      <Card title="Package status">
        <DeliverySteps status={data.status} events={data.timeline} />
      </Card>

      {onTheRoad ? (
        <>
          <Card title="Proof of delivery">
            <div className="flex flex-col gap-3">
              <PhotoPicker
                label="Photo of the parcel at the door or with the customer"
                value={photos}
                onChange={(files) => {
                  setPhotos(files);
                  setPhotoError(undefined);
                }}
                error={photoError}
              />
              <TextAreaField
                label="Note (optional)"
                placeholder="e.g. Left with the building guard"
                value={note}
                onChange={(event) => setNote(event.target.value)}
                rows={2}
              />
            </div>
          </Card>
          {deliver.isError && <Alert tone="danger">{errorMessage(deliver.error)}</Alert>}
          <div className="grid grid-cols-2 gap-3">
            <Button variant="secondary" size="lg" className="border-primary-600 text-primary-600" onClick={() => setFailing(true)}>
              Delivery failed
            </Button>
            <Button
              size="lg"
              loading={deliver.isPending}
              onClick={() => {
                if (!photos.length) {
                  setPhotoError("Add at least one photo as proof of delivery.");
                  return;
                }
                deliver.mutate(
                  { orderId, data: { photo_file_ids: photos.map((photo) => photo.id), note: note.trim() || null } },
                  { onSuccess: () => navigate(`/driver/orders/${orderId}/done`) },
                );
              }}
            >
              Successful
            </Button>
          </div>
          <Link to={`/driver/orders/${orderId}/eta`} className="text-center text-sm font-semibold text-primary-600">
            Running late? Update the delivery time
          </Link>
        </>
      ) : (
        <Alert tone="info">
          {data.status === "ASSIGNED" || data.status === "PICKED_UP"
            ? "Scan the parcel and start the delivery from the route screen first."
            : "This order is no longer out for delivery."}
        </Alert>
      )}

      <Dialog open={failing} title="Delivery failed" onClose={() => setFailing(false)}>
        <FailForm
          submitting={fail.isPending}
          error={fail.error}
          onCancel={() => setFailing(false)}
          onSubmit={(values) =>
            fail.mutate(
              { orderId, data: values },
              { onSuccess: () => navigate(`/driver/orders/${orderId}/done?result=failed`) },
            )
          }
        />
      </Dialog>
    </div>
  );
}
