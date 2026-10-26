// Hub hooks - live board queries (refreshed by realtime events) and order actions

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { errorMessage } from "@/lib/errors";
import { toast } from "@/lib/toast";
import type { HubOrderDetail } from "@/types";
import {
  confirmReturned,
  fetchDashboard,
  fetchDriverRoute,
  fetchOrder,
  fetchOrderCandidates,
  fetchRoute,
  holdOrder,
  listDrivers,
  listOrders,
  listRoutes,
  optimizeRoute,
  reassignOrder,
  releaseHold,
  saveStopOrder,
  type OrderFilters,
} from "./api";

// Realtime events refresh these; the interval is a safety net when the socket is down.
const LIVE = 60_000;

export function useDashboard() {
  return useQuery({ queryKey: ["hub", "dashboard"], queryFn: fetchDashboard, refetchInterval: LIVE });
}

export function useHubOrders(filters: OrderFilters) {
  return useQuery({
    queryKey: ["hub", "orders", filters],
    queryFn: () => listOrders(filters),
    placeholderData: keepPreviousData,
    refetchInterval: LIVE,
  });
}

export function useHubOrder(orderId: string | undefined) {
  return useQuery({
    queryKey: ["hub", "order", orderId],
    queryFn: () => fetchOrder(orderId ?? ""),
    enabled: Boolean(orderId),
  });
}

export function useHubDrivers() {
  return useQuery({ queryKey: ["hub", "drivers"], queryFn: listDrivers, refetchInterval: 30_000 });
}

export function useDriverRoute(driverId: string | null) {
  return useQuery({
    queryKey: ["hub", "driver-route", driverId],
    queryFn: () => fetchDriverRoute(driverId ?? ""),
    enabled: Boolean(driverId),
  });
}

export function useOrderCandidates(orderId: string, enabled: boolean) {
  return useQuery({
    queryKey: ["hub", "candidates", orderId],
    queryFn: () => fetchOrderCandidates(orderId),
    enabled,
    staleTime: 10_000,
  });
}

function useOrderAction<T>(action: (input: T) => Promise<HubOrderDetail>, success: (order: HubOrderDetail) => string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: action,
    onSuccess: (order) => {
      queryClient.setQueryData(["hub", "order", order.id], order);
      void queryClient.invalidateQueries({ queryKey: ["hub"] });
      toast.success(success(order));
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useReassign() {
  return useOrderAction(
    ({ orderId, driverId }: { orderId: string; driverId: string }) => reassignOrder(orderId, driverId),
    (order) => `Offer for ${order.waybill_code} sent. Waiting for the driver to accept.`,
  );
}

export function useHold() {
  return useOrderAction(
    ({ orderId, reason }: { orderId: string; reason: string }) => holdOrder(orderId, reason),
    (order) => `${order.waybill_code} is kept at the hub.`,
  );
}

export function useReleaseHold() {
  return useOrderAction(releaseHold, (order) => `${order.waybill_code} is back in dispatch.`);
}

export function useConfirmReturned() {
  return useOrderAction(confirmReturned, (order) => `${order.waybill_code} is back on the shelf.`);
}

// =============================== Route planning (H-02) ===============================

export function useRoutes() {
  return useQuery({ queryKey: ["hub", "routes"], queryFn: () => listRoutes(), refetchInterval: LIVE });
}

export function useRouteDetail(routeId: string | null) {
  return useQuery({
    queryKey: ["hub", "route", routeId],
    queryFn: () => fetchRoute(routeId ?? ""),
    enabled: Boolean(routeId),
  });
}

export function useOptimizeRoute() {
  return useMutation({ mutationFn: optimizeRoute, onError: (error) => toast.error(errorMessage(error)) });
}

export function useSaveStopOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ routeId, stopIds }: { routeId: string; stopIds: string[] }) => saveStopOrder(routeId, stopIds),
    onSuccess: (route) => {
      queryClient.setQueryData(["hub", "route", route.id], route);
      void queryClient.invalidateQueries({ queryKey: ["hub"] });
      toast.success(`New stop order sent to ${route.driver_name}. ETAs were updated.`);
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}
