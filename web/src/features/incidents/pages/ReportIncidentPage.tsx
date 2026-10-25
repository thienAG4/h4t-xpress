// ReportIncidentPage - D-11 (Figma "Report Issue"): reason, description, photos and the
// parcels affected, then the "REPORT!" popup. The customer receives an apology by webhook.

import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { PhotoPicker } from "@/components/PhotoPicker";
import { ScreenTitle } from "@/components/ScreenTitle";
import { Alert, Button, Card, Dialog, Loading, SelectField, TextAreaField } from "@/components/ui";
import { useRoute } from "@/features/delivery/hooks";
import { errorMessage } from "@/lib/errors";
import { currentPosition } from "@/lib/geo";
import { INCIDENT_TYPE, ORDER_STATUS, REPORTABLE_TYPES } from "@/lib/labels";
import type { DriverOrder, Incident, IncidentType, UploadedFile } from "@/types";
import { useReportIncident } from "../hooks";

const MIN_DESCRIPTION = 10;

export function ReportIncidentPage() {
  const [params] = useSearchParams();
  const route = useRoute();

  if (route.isPending) return <Loading />;
  if (route.isError) return <Alert tone="danger">{errorMessage(route.error)}</Alert>;

  // Every parcel the driver holds: still to collect, scanned, or on the road.
  const inHand: DriverOrder[] = [
    ...route.data.to_pick_up,
    ...route.data.stops.flatMap((stop) => stop.orders.filter((order) => order.status !== "ASSIGNED")),
  ];
  return <ReportForm orders={inHand} preselected={params.get("order")} />;
}

function ReportForm({ orders, preselected }: { orders: DriverOrder[]; preselected: string | null }) {
  const navigate = useNavigate();
  const report = useReportIncident();
  const [type, setType] = useState<IncidentType | "">("");
  const [description, setDescription] = useState("");
  const [photos, setPhotos] = useState<UploadedFile[]>([]);
  const [selected, setSelected] = useState<string[]>(() =>
    preselected && orders.some((order) => order.id === preselected) ? [preselected] : orders.map((order) => order.id),
  );
  const [errors, setErrors] = useState<{ type?: string; description?: string; photos?: string; orders?: string }>({});
  const [sent, setSent] = useState<Incident | null>(null);

  async function submit() {
    // Same order as the If-Else of the report: reason, description, evidence, then orders.
    const found = {
      type: type ? undefined : "Choose what happened.",
      description:
        description.trim().length >= MIN_DESCRIPTION ? undefined : `Describe the problem (at least ${MIN_DESCRIPTION} characters).`,
      photos: photos.length ? undefined : "Add at least one photo as evidence.",
      orders: selected.length ? undefined : "Choose the parcels affected.",
    };
    setErrors(found);
    if (Object.values(found).some(Boolean) || !type) return;
    const position = await currentPosition(3_000);
    report.mutate(
      {
        type,
        description: description.trim(),
        photo_file_ids: photos.map((photo) => photo.id),
        order_ids: selected,
        lat: position?.lat,
        lng: position?.lng,
      },
      { onSuccess: setSent },
    );
  }

  const firstOnRoad = orders.find((order) => selected.includes(order.id) && order.status === "OUT_FOR_DELIVERY");

  if (!orders.length) {
    return (
      <>
        <ScreenTitle title="Report Issue" back="/driver/incidents" />
        <Alert tone="info">You have no parcel in hand, so there is nothing to report on.</Alert>
      </>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <ScreenTitle title="Report Issue" back="/driver/route" />

      <Card>
        <SelectField
          label="Select reason"
          placeholder="Select a reason"
          options={REPORTABLE_TYPES.map((value) => ({ value, label: INCIDENT_TYPE[value] }))}
          value={type}
          onChange={(event) => setType(event.target.value as IncidentType)}
          error={errors.type}
        />
      </Card>

      <TextAreaField
        label="Description"
        placeholder="What happened, where, and can you continue?"
        rows={4}
        maxLength={1000}
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        error={errors.description}
      />

      <PhotoPicker
        label="Upload photo"
        value={photos}
        onChange={(files) => {
          setPhotos(files);
          setErrors((current) => ({ ...current, photos: undefined }));
        }}
        error={errors.photos}
      />

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-xs text-ink">Parcels affected</legend>
        {orders.map((order) => (
          <label key={order.id} className="flex items-center gap-3 rounded-input border border-line bg-white px-3 py-2 text-sm">
            <input
              type="checkbox"
              className="size-4 accent-primary-600"
              checked={selected.includes(order.id)}
              onChange={(event) =>
                setSelected((current) =>
                  event.target.checked ? [...current, order.id] : current.filter((id) => id !== order.id),
                )
              }
            />
            <span className="font-semibold">{order.waybill_code}</span>
            <span className="truncate text-neutral-600">{ORDER_STATUS[order.status].label}</span>
          </label>
        ))}
        {errors.orders && <p className="text-xs text-danger-500">{errors.orders}</p>}
      </fieldset>

      {report.isError && <Alert tone="danger">{errorMessage(report.error)}</Alert>}
      <div className="grid grid-cols-2 gap-3">
        <Button size="lg" loading={report.isPending} onClick={() => void submit()}>
          Confirm
        </Button>
        <Button variant="secondary" size="lg" onClick={() => navigate(-1)}>
          Cancel
        </Button>
      </div>

      <Dialog
        open={Boolean(sent)}
        title="REPORT!"
        onClose={() => navigate("/driver/incidents")}
        actions={
          <>
            <Link
              to="/driver/incidents"
              className="inline-flex h-10 items-center rounded-button border border-line px-4 text-sm font-semibold"
            >
              Back
            </Link>
            {firstOnRoad && (
              <Link
                to={`/driver/orders/${firstOnRoad.id}/eta`}
                className="inline-flex h-10 items-center rounded-button bg-primary-600 px-4 text-sm font-semibold text-white"
              >
                Update time delivery
              </Link>
            )}
          </>
        }
      >
        <p>
          {sent?.code}: {sent?.orders.map((order) => order.waybill_code).join(", ")} has been reported successfully. The
          hub will answer you here.
        </p>
      </Dialog>
    </div>
  );
}
