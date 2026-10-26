// OfferModal - D-06: full-screen job offer with a countdown, Accept or Decline (BR7, BR8)

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { Badge, Button, SelectField } from "@/components/ui";
import { formatKm, formatMoney } from "@/lib/format";
import type { Offer } from "@/types";
import { OFFER_KEY, useAcceptOffer, useCurrentOffer, useDeclineOffer } from "../hooks";

const DECLINE_REASONS = [
  { value: "Too far from my position", label: "Too far from my position" },
  { value: "Vehicle is full", label: "Vehicle is full" },
  { value: "Ending my shift soon", label: "Ending my shift soon" },
  { value: "Other", label: "Other" },
];

/** Seconds left, counted locally from the moment the offer was fetched (no clock skew). */
function useSecondsLeft(offer: Offer | null | undefined, fetchedAt: number): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!offer) return;
    const timer = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(timer);
  }, [offer]);
  if (!offer) return 0;
  return Math.max(0, Math.ceil((fetchedAt + offer.seconds_left * 1000 - now) / 1000));
}

export function OfferModal({ enabled }: { enabled: boolean }) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const offerQuery = useCurrentOffer(enabled);
  const offer = offerQuery.data;
  const secondsLeft = useSecondsLeft(offer, offerQuery.dataUpdatedAt);

  const expired = Boolean(offer) && secondsLeft === 0;
  useEffect(() => {
    if (expired) void queryClient.invalidateQueries({ queryKey: OFFER_KEY });
  }, [expired, queryClient]);

  if (!offer || expired) return null;
  // Keyed by offer: a new offer starts with a fresh form. The sheet unmounts as soon as the
  // offer is gone, so navigation after accepting is done here, by the parent.
  return (
    <OfferSheet
      key={offer.id}
      offer={offer}
      secondsLeft={secondsLeft}
      onAccepted={() => navigate("/driver/route")}
    />
  );
}

type SheetProps = { offer: Offer; secondsLeft: number; onAccepted: () => void };

function OfferSheet({ offer, secondsLeft, onAccepted }: SheetProps) {
  const accept = useAcceptOffer();
  const decline = useDeclineOffer();
  const [declining, setDeclining] = useState(false);
  const [reason, setReason] = useState("");
  const [total] = useState(() => Math.max(secondsLeft, 1));
  const busy = accept.isPending || decline.isPending;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="offer-title"
      className="fixed inset-0 z-50 flex items-end justify-center bg-neutral-900/50 sm:items-center"
    >
      <div className="w-full max-w-[430px] rounded-t-sheet bg-white p-5 shadow-xl sm:rounded-sheet">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold tracking-wide text-primary-600 uppercase">
              {offer.is_rescue ? "Rescue request from the hub" : offer.source === "MANUAL" ? "Offer from the hub" : "New delivery offer"}
            </p>
            <h2 id="offer-title" className="mt-1 text-xl font-bold">
              {offer.order_count === 1 ? offer.waybill_codes[0] : `${offer.order_count} parcels`}
            </h2>
          </div>
          <div className="text-right" aria-live="polite">
            <p className="font-display text-3xl font-bold text-primary-600">{secondsLeft}s</p>
            <p className="text-xs text-neutral-500">to answer</p>
          </div>
        </div>
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-neutral-100">
          <div
            className="h-full rounded-full bg-primary-600 transition-[width] duration-300"
            style={{ width: `${(secondsLeft / total) * 100}%` }}
          />
        </div>

        <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
          <div className="col-span-2">
            <dt className="text-xs text-neutral-500">{offer.is_rescue ? "Collect from" : "Pick up at"}</dt>
            <dd className="font-medium">{offer.pickup_label}</dd>
          </div>
          <div className="col-span-2">
            <dt className="text-xs text-neutral-500">Deliver to</dt>
            {offer.delivery_addresses.map((address) => (
              <dd key={address} className="font-medium">
                {address}
              </dd>
            ))}
          </div>
          <div>
            <dt className="text-xs text-neutral-500">Distance to pickup</dt>
            <dd className="font-medium">{formatKm(offer.distance_km)}</dd>
          </div>
          <div>
            <dt className="text-xs text-neutral-500">Cash to collect</dt>
            <dd className="font-medium">{formatMoney(offer.cod_total)}</dd>
          </div>
        </dl>
        {offer.priority === "EXPRESS" && (
          <div className="mt-3">
            <Badge tone="danger">Express delivery</Badge>
          </div>
        )}

        {declining ? (
          <div className="mt-5 flex flex-col gap-3">
            <SelectField
              label="Why are you declining? (optional)"
              placeholder="Choose a reason"
              options={DECLINE_REASONS}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
            <div className="grid grid-cols-2 gap-3">
              <Button variant="secondary" size="lg" disabled={busy} onClick={() => setDeclining(false)}>
                Back
              </Button>
              <Button
                variant="danger"
                size="lg"
                loading={decline.isPending}
                onClick={() => decline.mutate({ offerId: offer.id, reason: reason || null })}
              >
                Decline
              </Button>
            </div>
          </div>
        ) : (
          <div className="mt-5 grid grid-cols-2 gap-3">
            <Button variant="secondary" size="lg" disabled={busy} onClick={() => setDeclining(true)}>
              Decline
            </Button>
            <Button
              size="lg"
              loading={accept.isPending}
              onClick={() => void accept.mutateAsync(offer.id).then(onAccepted, () => undefined)}
            >
              Accept
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
