// Hub API - dashboard, order board, drivers, manual dispatch (H-01, H-03, H-07), routes (H-02)

import { request } from "@/lib/http";
import type {
  Candidate,
  DriverRoute,
  HubDashboard,
  HubDriverRow,
  HubOrderDetail,
  HubOrderRow,
  OptimizeResult,
  OrderStatus,
  Page,
  RouteDetail,
  RouteSummary,
} from "@/types";

export type OrderFilters = {
  page: number;
  page_size: number;
  status?: OrderStatus;
  at_risk?: boolean;
  q?: string;
};

export function fetchDashboard(): Promise<HubDashboard> {
  return request<HubDashboard>("/hub/dashboard");
}

export function listOrders(filters: OrderFilters): Promise<Page<HubOrderRow>> {
  return request<Page<HubOrderRow>>("/hub/orders", { query: filters });
}

export function fetchOrder(orderId: string): Promise<HubOrderDetail> {
  return request<HubOrderDetail>(`/hub/orders/${orderId}`);
}

export function listDrivers(): Promise<HubDriverRow[]> {
  return request<HubDriverRow[]>("/hub/drivers");
}

export function fetchDriverRoute(driverId: string): Promise<DriverRoute> {
  return request<DriverRoute>(`/hub/drivers/${driverId}/route`);
}

export function fetchOrderCandidates(orderId: string): Promise<Candidate[]> {
  return request<Candidate[]>(`/hub/orders/${orderId}/candidates`);
}

export function reassignOrder(orderId: string, driverId: string): Promise<HubOrderDetail> {
  return request<HubOrderDetail>(`/hub/orders/${orderId}/reassign`, {
    method: "POST",
    body: { driver_id: driverId },
  });
}

export function holdOrder(orderId: string, reason: string): Promise<HubOrderDetail> {
  return request<HubOrderDetail>(`/hub/orders/${orderId}/hold`, { method: "POST", body: { reason } });
}

export function releaseHold(orderId: string): Promise<HubOrderDetail> {
  return request<HubOrderDetail>(`/hub/orders/${orderId}/release-hold`, { method: "POST" });
}

export function confirmReturned(orderId: string): Promise<HubOrderDetail> {
  return request<HubOrderDetail>(`/hub/orders/${orderId}/returned`, { method: "POST" });
}

// =============================== Route planning (H-02) ===============================

export function listRoutes(workDate?: string): Promise<RouteSummary[]> {
  return request<RouteSummary[]>("/hub/routes", { query: { work_date: workDate } });
}

export function fetchRoute(routeId: string): Promise<RouteDetail> {
  return request<RouteDetail>(`/hub/routes/${routeId}`);
}

export function optimizeRoute(routeId: string): Promise<OptimizeResult> {
  return request<OptimizeResult>(`/hub/routes/${routeId}/optimize`, { method: "POST" });
}

export function saveStopOrder(routeId: string, stopIds: string[]): Promise<RouteDetail> {
  return request<RouteDetail>(`/hub/routes/${routeId}/stops/order`, {
    method: "PUT",
    body: { stop_ids: stopIds },
  });
}
