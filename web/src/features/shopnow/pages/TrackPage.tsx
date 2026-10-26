// TrackPage - S-03: ShopNow's customer tracking page. Everything shown comes from the
// webhooks ShopNow received: status, new ETA, the reason of a delay with an apology.

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { Alert, Button, Loading, TextField } from "@/components/ui";
import { cn } from "@/lib/cn";
import { errorCode, errorMessage } from "@/lib/errors";
import { formatDateTime, formatPhone } from "@/lib/format";
import type { TrackPage as TrackData } from "@/types";
import { fetchTracking } from "../api";

function Summary({ data }: { data: TrackData }) {
  const delivered = data.status === "DELIVERED";
  return (
    <section className="rounded-card border border-line bg-white p-5">
      <p className="text-xs text-neutral-500">
        Order {data.partner_order_ref} - waybill {data.waybill_code}
      </p>
      <h1 className={cn("mt-1 text-2xl font-bold", delivered ? "text-success-700" : "text-shop-700")}>{data.status_label}</h1>
      <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
        <div>
          <dt className="text-xs text-neutral-500">{delivered ? "Delivered at" : "Expected"}</dt>
          <dd className="font-semibold">
            {formatDateTime(data.eta ?? data.promised_at)}
            {data.eta_is_estimate && !delivered ? " (estimate)" : ""}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-neutral-500">Promised by</dt>
          <dd className="font-semibold">{formatDateTime(data.promised_at)}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-xs text-neutral-500">Deliver to</dt>
          <dd>
            {data.recipient_name}, {data.delivery_address}
          </dd>
        </div>
        {data.driver && (
          <div className="col-span-2">
            <dt className="text-xs text-neutral-500">Your driver</dt>
            <dd>
              {data.driver.name}
              {data.driver.phone && !delivered && (
                <a href={`tel:${data.driver.phone}`} className="ml-2 font-semibold text-shop-700">
                  Call {formatPhone(data.driver.phone)}
                </a>
              )}
            </dd>
          </div>
        )}
      </dl>
      {data.delay_message && (
        <Alert tone="warning" title={data.is_late ? "Your parcel is running late" : "Update on your delivery"} className="mt-4">
          {data.delay_message}
        </Alert>
      )}
      {data.proof_url && (
        <figure className="mt-4">
          <img src={data.proof_url} alt="Parcel at delivery" className="max-h-64 rounded-input border border-line object-cover" />
          <figcaption className="mt-1 text-xs text-neutral-500">Photo taken by the driver at delivery</figcaption>
        </figure>
      )}
    </section>
  );
}

function Steps({ data }: { data: TrackData }) {
  return (
    <section className="rounded-card border border-line bg-white p-5">
      <h2 className="text-base font-semibold">Tracking history</h2>
      <ol className="mt-4 flex flex-col gap-4 border-l border-line pl-5">
        {data.steps.map((step, index) => (
          <li key={`${step.at}-${index}`} className="relative">
            <span
              className={cn(
                "absolute top-1.5 -left-[25px] size-2.5 rounded-full",
                index === 0 ? "bg-shop-600" : "bg-neutral-300",
                step.event === "order.incident" && "bg-danger-500",
              )}
            />
            <p className={cn("text-sm", index === 0 ? "font-semibold" : "text-neutral-700")}>{step.title}</p>
            <p className="text-xs text-neutral-500">{formatDateTime(step.at)}</p>
            {step.message && <p className="mt-0.5 text-xs text-neutral-600">{step.message}</p>}
          </li>
        ))}
      </ol>
    </section>
  );
}

export function TrackPage() {
  const { waybill = "" } = useParams();
  const navigate = useNavigate();
  const [code, setCode] = useState(waybill);
  const tracking = useQuery({
    queryKey: ["track", waybill],
    queryFn: () => fetchTracking(waybill),
    enabled: Boolean(waybill),
    refetchInterval: 15_000,
    retry: false,
  });

  return (
    <div className="min-h-full bg-shop-50/40">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-2xl items-center justify-between px-4 py-4">
          <Link to="/shopnow" className="font-display text-xl font-extrabold text-shop-600">
            ShopNow
          </Link>
          <span className="text-xs text-neutral-600">Delivered by H4T Xpress</span>
        </div>
      </header>
      <main className="mx-auto flex max-w-2xl flex-col gap-4 px-4 py-6">
        <form
          className="flex gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            if (code.trim()) navigate(`/track/${code.trim().toUpperCase()}`);
          }}
        >
          <div className="flex-1">
            <TextField compact aria-label="Waybill code" placeholder="Enter your waybill code" value={code} onChange={(event) => setCode(event.target.value)} />
          </div>
          <Button type="submit" className="bg-shop-600 hover:bg-shop-700">
            Track
          </Button>
        </form>

        {tracking.isPending && waybill && <Loading />}
        {tracking.isError && (
          <Alert tone={errorCode(tracking.error) === "ORDER_NOT_FOUND" ? "warning" : "danger"}>
            {errorCode(tracking.error) === "ORDER_NOT_FOUND"
              ? "We could not find this waybill. Check the code on your order e-mail."
              : errorMessage(tracking.error)}
          </Alert>
        )}
        {tracking.data && (
          <>
            <Summary data={tracking.data} />
            <Steps data={tracking.data} />
          </>
        )}
      </main>
    </div>
  );
}
