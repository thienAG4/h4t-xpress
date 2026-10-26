// ShopNow API - the simulated partner (S-01..S-03) and the demo control panel (S-04)

import { request } from "@/lib/http";
import type { DemoStatus, ManualOrderInput, Page, SimOrder, SimWebhook, TrackPage } from "@/types";

export function createRandomOrders(hubCode: string, count: number): Promise<SimOrder[]> {
  return request<SimOrder[]>("/sim/shopnow/orders/random", {
    method: "POST",
    body: { hub_code: hubCode, count },
    auth: false,
  });
}

export function createManualOrder(data: ManualOrderInput): Promise<SimOrder> {
  return request<SimOrder>("/sim/shopnow/orders", { method: "POST", body: data, auth: false });
}

export function listOrders(page: number, pageSize = 10): Promise<Page<SimOrder>> {
  return request<Page<SimOrder>>("/sim/shopnow/orders", {
    query: { page, page_size: pageSize },
    auth: false,
  });
}

export function cancelOrder(waybillCode: string): Promise<SimOrder> {
  return request<SimOrder>(`/sim/shopnow/orders/${waybillCode}/cancel`, { method: "POST", auth: false });
}

export function listWebhooks(page: number, pageSize = 10): Promise<Page<SimWebhook>> {
  return request<Page<SimWebhook>>("/sim/shopnow/webhooks", {
    query: { page, page_size: pageSize },
    auth: false,
  });
}

export function fetchTracking(waybillCode: string): Promise<TrackPage> {
  return request<TrackPage>(`/sim/track/${encodeURIComponent(waybillCode)}`, { auth: false });
}

// =============================== Demo control panel (S-04) ===============================

export function fetchDemoStatus(): Promise<DemoStatus> {
  return request<DemoStatus>("/sim/demo", { auth: false });
}

export function switchGps(enabled: boolean): Promise<DemoStatus> {
  return request<DemoStatus>("/sim/demo/gps", { method: "PUT", body: { enabled }, auth: false });
}

export function startTrafficJam(driverId: string): Promise<DemoStatus> {
  return request<DemoStatus>("/sim/demo/traffic-jam", { method: "POST", body: { driver_id: driverId }, auth: false });
}

/** System admin only: reloads every demo row and signs everyone out. */
export function resetDemo(): Promise<{ rows: number }> {
  return request<{ rows: number }>("/sim/demo/reset", { method: "POST" });
}
