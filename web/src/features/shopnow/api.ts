// ShopNow API - the simulated e-commerce partner (S-01..S-03); demo deployments only

import { request } from "@/lib/http";
import type { ManualOrderInput, Page, SimOrder, SimWebhook, TrackPage } from "@/types";

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
