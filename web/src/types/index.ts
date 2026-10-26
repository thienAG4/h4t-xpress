// Shared API types - short aliases over the schema generated from the backend OpenAPI

import type { components } from "./api";

type Schemas = components["schemas"];

export type Me = Schemas["MeOut"];
export type User = Schemas["UserOut"];
export type UserCreateInput = Schemas["UserCreateIn"];
export type UserUpdateInput = Schemas["UserUpdateIn"];
export type Hub = Schemas["HubOut"];
export type Role = Schemas["RoleOut"];
export type Permission = Schemas["PermissionOut"];
export type TokenResponse = Schemas["TokenOut"];
export type OtpSent = Schemas["OtpSentOut"];
export type RegisterDriverInput = Schemas["RegisterDriverIn"];
export type DriverToday = Schemas["DriverTodayOut"];
export type ShiftDay = Schemas["ShiftDayOut"];
export type ShiftSlot = Schemas["ShiftSlotOut"];
export type Registration = Schemas["RegistrationOut"];
export type SimOrder = Schemas["SimOrderOut"];
export type SimWebhook = Schemas["SimWebhookOut"];
export type ManualOrderInput = Schemas["ManualOrderIn"];
export type RoleCode = Schemas["RoleCode"];

// Phase 2: dispatch, delivery, incidents, hub monitoring, tracking page
export type OrderStatus = Schemas["OrderStatus"];
export type OrderPriority = Schemas["OrderPriority"];
export type FailureReason = Schemas["FailureReason"];
export type StopStatus = Schemas["StopStatus"];
export type Offer = Schemas["OfferOut"];
export type DriverOrder = Schemas["DriverOrderOut"];
export type DriverOrderDetail = Schemas["DriverOrderDetailOut"];
export type DriverRoute = Schemas["RouteOut"];
export type RouteStop = Schemas["StopOut"];
export type TimelineEvent = Schemas["TimelineEventOut"];
export type UploadedFile = Schemas["FileOut"];
export type DeliverInput = Schemas["DeliverIn"];
export type FailInput = Schemas["FailIn"];
export type EtaInput = Schemas["EtaIn"];
export type HubDashboard = Schemas["DashboardOut"];
export type HubOrderRow = Schemas["HubOrderRow"];
export type HubOrderDetail = Schemas["HubOrderDetail"];
export type HubDriverRow = Schemas["HubDriverRow"];
export type Candidate = Schemas["CandidateOut"];
export type IncidentType = Schemas["IncidentType"];
export type IncidentStatus = Schemas["IncidentStatus"];
export type IncidentCategory = Schemas["IncidentCategory"];
export type IncidentPriority = Schemas["IncidentPriority"];
export type ResolutionSolution = Schemas["ResolutionSolution"];
export type Incident = Schemas["IncidentOut"];
export type IncidentListItem = Schemas["IncidentListItem"];
export type IncidentSummary = Schemas["IncidentSummaryOut"];
export type IncidentReportInput = Schemas["IncidentReportIn"];
export type ResolveInput = Schemas["ResolveIn"];
export type TrackPage = Schemas["TrackOut"];

// Phase 3: route planning, reports, configuration, demo panel
export type RouteSummary = Schemas["RouteSummaryOut"];
export type RouteDetail = Schemas["RouteDetailOut"];
export type PlanStop = Schemas["PlanStopOut"];
export type OptimizeResult = Schemas["OptimizeOut"];
export type Report = Schemas["ReportOut"];
export type ReportKpi = Schemas["KpiOut"];
export type Granularity = Schemas["Granularity"];
export type AdminArea = Schemas["AreaOut"];
export type AreaInput = Schemas["AreaIn"];
export type AdminHub = Schemas["AdminHubOut"];
export type HubInput = Schemas["HubIn"];
export type AdminShift = Schemas["ShiftOut"];
export type ShiftUpdateInput = Schemas["ShiftUpdateIn"];
export type Setting = Schemas["SettingOut"];
export type AuditEntry = Schemas["AuditOut"];
export type DemoStatus = Schemas["DemoStatusOut"];

export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};
