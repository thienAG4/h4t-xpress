// Delivery hooks - React Query wrappers for the driver order flow, plus the presence heartbeat

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { errorMessage } from "@/lib/errors";
import { currentPosition, distanceKm } from "@/lib/geo";
import { toast } from "@/lib/toast";
import type { DeliverInput, EtaInput, FailInput } from "@/types";
import {
  acceptOffer,
  declineOffer,
  deliverOrder,
  failOrder,
  fetchCurrentOffer,
  fetchOrder,
  fetchRoute,
  releaseOrder,
  scanOrder,
  sendHeartbeat,
  startRoute,
  updateEta,
} from "./api";

export const OFFER_KEY = ["delivery", "offer"];
export const ROUTE_KEY = ["delivery", "route"];
const orderKey = (orderId: string) => ["delivery", "order", orderId];

const HEARTBEAT_MS = 15_000;
// Demo data lives around Ho Chi Minh City. A browser far away (a reviewer abroad) keeps
// the seeded position instead of moving the driver across the country.
const DEMO_RADIUS_KM = 50;

// =============================== Queries ===============================

/** The open offer. Polls as a fallback when the WebSocket is down. */
export function useCurrentOffer(enabled: boolean) {
  return useQuery({
    queryKey: OFFER_KEY,
    queryFn: fetchCurrentOffer,
    enabled,
    refetchInterval: enabled ? 10_000 : false,
    staleTime: 0,
  });
}

export function useRoute() {
  return useQuery({ queryKey: ROUTE_KEY, queryFn: fetchRoute, refetchInterval: 30_000 });
}

export function useDriverOrder(orderId: string) {
  return useQuery({ queryKey: orderKey(orderId), queryFn: () => fetchOrder(orderId) });
}

// =============================== Presence ===============================

/** While online, tell the server every 15 s that the app is open, with GPS when allowed. */
export function useHeartbeat(online: boolean, hub: { lat: number; lng: number } | null) {
  const hubLat = hub?.lat;
  const hubLng = hub?.lng;
  useEffect(() => {
    if (!online) return;
    let cancelled = false;
    const beat = async () => {
      const position = await currentPosition();
      const nearHub =
        position && hubLat !== undefined && hubLng !== undefined
          ? distanceKm(position, { lat: hubLat, lng: hubLng }) <= DEMO_RADIUS_KM
          : false;
      if (!cancelled) await sendHeartbeat(nearHub ? position : null).catch(() => undefined);
    };
    void beat();
    const timer = window.setInterval(() => void beat(), HEARTBEAT_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [online, hubLat, hubLng]);
}

// =============================== Mutations ===============================

function useRefreshDelivery() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: ["delivery"] });
    void queryClient.invalidateQueries({ queryKey: ["driver", "today"] });
  };
}

export function useAcceptOffer() {
  const refresh = useRefreshDelivery();
  return useMutation({
    mutationFn: acceptOffer,
    onSuccess: () => {
      toast.success("Order accepted. It is on your route.");
      refresh();
    },
    onError: (error) => {
      toast.error(errorMessage(error));
      refresh();
    },
  });
}

export function useDeclineOffer() {
  const refresh = useRefreshDelivery();
  return useMutation({
    mutationFn: ({ offerId, reason }: { offerId: string; reason: string | null }) => declineOffer(offerId, reason),
    onSuccess: () => {
      toast.info("Offer declined.");
      refresh();
    },
    onError: (error) => {
      toast.error(errorMessage(error));
      refresh();
    },
  });
}

export function useScanOrder() {
  const refresh = useRefreshDelivery();
  return useMutation({
    mutationFn: async ({ orderId, waybillCode }: { orderId: string; waybillCode: string }) =>
      scanOrder(orderId, waybillCode, await currentPosition(2_000)),
    onSuccess: (order) => {
      toast.success(`Parcel ${order.waybill_code} scanned.`);
      refresh();
    },
  });
}

export function useStartRoute() {
  const refresh = useRefreshDelivery();
  return useMutation({
    mutationFn: startRoute,
    onSuccess: ({ started }) => {
      toast.success(`${started} parcel${started === 1 ? "" : "s"} out for delivery.`);
      refresh();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useDeliverOrder() {
  const refresh = useRefreshDelivery();
  return useMutation({
    mutationFn: async ({ orderId, data }: { orderId: string; data: Omit<DeliverInput, "lat" | "lng"> }) => {
      const position = await currentPosition(2_000);
      return deliverOrder(orderId, { ...data, lat: position?.lat, lng: position?.lng });
    },
    onSuccess: refresh,
  });
}

export function useFailOrder() {
  const refresh = useRefreshDelivery();
  return useMutation({
    mutationFn: ({ orderId, data }: { orderId: string; data: FailInput }) => failOrder(orderId, data),
    onSuccess: refresh,
  });
}

export function useUpdateEta() {
  const refresh = useRefreshDelivery();
  return useMutation({
    mutationFn: ({ orderId, data }: { orderId: string; data: EtaInput }) => updateEta(orderId, data),
    onSuccess: refresh,
  });
}

export function useReleaseOrder() {
  const refresh = useRefreshDelivery();
  return useMutation({
    mutationFn: ({ orderId, reason }: { orderId: string; reason: string }) => releaseOrder(orderId, reason),
    onSuccess: () => {
      toast.info("Order given back. Dispatch will find another driver.");
      refresh();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}
