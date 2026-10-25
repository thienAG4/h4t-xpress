// Delivery API - driver offers, today's route and order actions (D-06..D-14)

import type { GeoPoint } from "@/lib/geo";
import { request } from "@/lib/http";
import type {
  DeliverInput,
  DriverOrder,
  DriverOrderDetail,
  DriverRoute,
  EtaInput,
  FailInput,
  Offer,
} from "@/types";

export function sendHeartbeat(position: GeoPoint | null): Promise<void> {
  return request<void>("/driver/heartbeat", { method: "POST", body: position ?? {} });
}

export function fetchCurrentOffer(): Promise<Offer | null> {
  return request<Offer | null>("/driver/offers/current");
}

export function acceptOffer(offerId: string): Promise<DriverRoute> {
  return request<DriverRoute>(`/driver/offers/${offerId}/accept`, { method: "POST" });
}

export function declineOffer(offerId: string, reason: string | null): Promise<void> {
  return request<void>(`/driver/offers/${offerId}/decline`, { method: "POST", body: { reason } });
}

export function fetchRoute(): Promise<DriverRoute> {
  return request<DriverRoute>("/driver/route");
}

export function startRoute(): Promise<{ started: number }> {
  return request<{ started: number }>("/driver/route/start", { method: "POST" });
}

export function fetchOrder(orderId: string): Promise<DriverOrderDetail> {
  return request<DriverOrderDetail>(`/driver/orders/${orderId}`);
}

export function scanOrder(orderId: string, waybillCode: string, position: GeoPoint | null): Promise<DriverOrder> {
  return request<DriverOrder>(`/driver/orders/${orderId}/scan`, {
    method: "POST",
    body: { waybill_code: waybillCode, lat: position?.lat, lng: position?.lng },
  });
}

export function deliverOrder(orderId: string, data: DeliverInput): Promise<DriverOrder> {
  return request<DriverOrder>(`/driver/orders/${orderId}/deliver`, { method: "POST", body: data });
}

export function failOrder(orderId: string, data: FailInput): Promise<DriverOrder> {
  return request<DriverOrder>(`/driver/orders/${orderId}/fail`, { method: "POST", body: data });
}

export function updateEta(orderId: string, data: EtaInput): Promise<DriverOrder> {
  return request<DriverOrder>(`/driver/orders/${orderId}/eta`, { method: "PUT", body: data });
}

export function releaseOrder(orderId: string, reason: string): Promise<void> {
  return request<void>(`/driver/orders/${orderId}/release`, { method: "POST", body: { reason } });
}
