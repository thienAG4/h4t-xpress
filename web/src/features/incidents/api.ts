// Incidents API - driver reports (D-11) and hub handling (H-04..H-08)

import { request } from "@/lib/http";
import type {
  Candidate,
  Incident,
  IncidentCategory,
  IncidentListItem,
  IncidentPriority,
  IncidentReportInput,
  IncidentStatus,
  IncidentSummary,
  Page,
  ResolveInput,
} from "@/types";

// =============================== Driver ===============================

export function reportIncident(data: IncidentReportInput): Promise<Incident> {
  return request<Incident>("/driver/incidents", { method: "POST", body: data });
}

export function listMyIncidents(): Promise<Incident[]> {
  return request<Incident[]>("/driver/incidents");
}

// =============================== Hub ===============================

export type IncidentFilters = {
  page: number;
  page_size: number;
  status?: IncidentStatus;
  priority?: IncidentPriority;
  open_only?: boolean;
};

export function fetchSummary(): Promise<IncidentSummary> {
  return request<IncidentSummary>("/hub/incidents/summary");
}

export function listIncidents(filters: IncidentFilters): Promise<Page<IncidentListItem>> {
  return request<Page<IncidentListItem>>("/hub/incidents", { query: filters });
}

export function fetchIncident(incidentId: string): Promise<Incident> {
  return request<Incident>(`/hub/incidents/${incidentId}`);
}

export function classifyIncident(
  incidentId: string,
  category: IncidentCategory,
  priority: IncidentPriority,
): Promise<Incident> {
  return request<Incident>(`/hub/incidents/${incidentId}/classify`, {
    method: "POST",
    body: { category, priority },
  });
}

export function respondIncident(incidentId: string, message: string): Promise<Incident> {
  return request<Incident>(`/hub/incidents/${incidentId}/respond`, { method: "POST", body: { message } });
}

export function fetchCandidates(incidentId: string): Promise<Candidate[]> {
  return request<Candidate[]>(`/hub/incidents/${incidentId}/candidates`);
}

export function resolveIncident(incidentId: string, data: ResolveInput): Promise<Incident> {
  return request<Incident>(`/hub/incidents/${incidentId}/resolve`, { method: "POST", body: data });
}
