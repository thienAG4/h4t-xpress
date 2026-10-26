// Incident hooks - queries and mutations shared by the driver report and the hub screens

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { IncidentCategory, IncidentPriority, ResolveInput } from "@/types";
import {
  classifyIncident,
  fetchCandidates,
  fetchIncident,
  fetchSummary,
  listIncidents,
  listMyIncidents,
  reportIncident,
  resolveIncident,
  respondIncident,
  type IncidentFilters,
} from "./api";

const incidentKey = (incidentId: string) => ["incidents", "detail", incidentId];

export function useMyIncidents() {
  return useQuery({ queryKey: ["incidents", "mine"], queryFn: listMyIncidents });
}

export function useReportIncident() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: reportIncident,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["incidents"] });
      void queryClient.invalidateQueries({ queryKey: ["delivery"] });
    },
  });
}

export function useIncidentSummary() {
  return useQuery({ queryKey: ["incidents", "summary"], queryFn: fetchSummary });
}

export function useIncidentList(filters: IncidentFilters) {
  return useQuery({
    queryKey: ["incidents", "list", filters],
    queryFn: () => listIncidents(filters),
    placeholderData: keepPreviousData,
  });
}

export function useIncident(incidentId: string) {
  return useQuery({ queryKey: incidentKey(incidentId), queryFn: () => fetchIncident(incidentId) });
}

export function useCandidates(incidentId: string, enabled: boolean) {
  return useQuery({
    queryKey: ["incidents", "candidates", incidentId],
    queryFn: () => fetchCandidates(incidentId),
    enabled,
    staleTime: 10_000,
  });
}

function useIncidentMutation<T>(incidentId: string, action: (input: T) => ReturnType<typeof fetchIncident>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: action,
    onSuccess: (incident) => {
      queryClient.setQueryData(incidentKey(incidentId), incident);
      void queryClient.invalidateQueries({ queryKey: ["incidents"] });
      void queryClient.invalidateQueries({ queryKey: ["hub"] });
    },
  });
}

export function useClassify(incidentId: string) {
  return useIncidentMutation(incidentId, (input: { category: IncidentCategory; priority: IncidentPriority }) =>
    classifyIncident(incidentId, input.category, input.priority),
  );
}

export function useRespond(incidentId: string) {
  return useIncidentMutation(incidentId, (message: string) => respondIncident(incidentId, message));
}

export function useResolve(incidentId: string) {
  return useIncidentMutation(incidentId, (data: ResolveInput) => resolveIncident(incidentId, data));
}
