// Router - public pages, sign-in flow and one guarded area per role (SPEC §4.3)

import { createBrowserRouter } from "react-router";
import { ComingSoon } from "@/components/ComingSoon";
import { RolesPage } from "@/features/admin/pages/RolesPage";
import { UserFormPage } from "@/features/admin/pages/UserFormPage";
import { UsersPage } from "@/features/admin/pages/UsersPage";
import { ForgotPasswordPage } from "@/features/auth/pages/ForgotPasswordPage";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { RegisterPage } from "@/features/auth/pages/RegisterPage";
import { VerifyOtpPage } from "@/features/auth/pages/VerifyOtpPage";
import { DonePage } from "@/features/delivery/pages/DonePage";
import { EtaPage } from "@/features/delivery/pages/EtaPage";
import { OrderPage } from "@/features/delivery/pages/OrderPage";
import { RoutePage } from "@/features/delivery/pages/RoutePage";
import { StopPage } from "@/features/delivery/pages/StopPage";
import { DriverHomePage } from "@/features/driver/pages/DriverHomePage";
import { ProfilePage } from "@/features/driver/pages/ProfilePage";
import { ShiftsPage } from "@/features/driver/pages/ShiftsPage";
import { HomePage } from "@/features/home/HomePage";
import { NotFoundPage } from "@/features/home/NotFoundPage";
import { HubDashboardPage } from "@/features/hub/pages/HubDashboardPage";
import { TrackingPage } from "@/features/hub/pages/TrackingPage";
import { IncidentDetailPage } from "@/features/incidents/pages/IncidentDetailPage";
import { IncidentListPage } from "@/features/incidents/pages/IncidentListPage";
import { IncidentsOverviewPage } from "@/features/incidents/pages/IncidentsOverviewPage";
import { MyIncidentsPage } from "@/features/incidents/pages/MyIncidentsPage";
import { ReportIncidentPage } from "@/features/incidents/pages/ReportIncidentPage";
import { ShopNowPage } from "@/features/shopnow/pages/ShopNowPage";
import { TrackPage } from "@/features/shopnow/pages/TrackPage";
import { RedirectIfSignedIn, RequireAuth } from "./guards";
import { AuthLayout } from "./layouts/AuthLayout";
import { DashboardLayout, type NavItem } from "./layouts/DashboardLayout";
import { DriverLayout } from "./layouts/DriverLayout";

const hubNav: NavItem[] = [
  { to: "/hub", label: "Dashboard", end: true },
  { to: "/hub/incidents", label: "Incidents", permission: "incident.manage" },
  { to: "/hub/tracking", label: "Delivery tracking" },
  { to: "/hub/routes", label: "Route planning", permission: "route.plan" },
  { to: "/reports", label: "Reports", permission: "report.view" },
];

const reportsNav: NavItem[] = [{ to: "/reports", label: "Overview", end: true }];

const adminNav: NavItem[] = [
  { to: "/admin", label: "Users", end: true, permission: "user.manage" },
  { to: "/admin/roles", label: "Roles & permissions", permission: "role.manage" },
  { to: "/admin/hubs", label: "Hubs & areas", permission: "hub.manage" },
  { to: "/admin/shifts", label: "Shifts", permission: "hub.manage" },
  { to: "/admin/settings", label: "Settings", permission: "settings.manage" },
];

const soon = (title: string, phase: string, description?: string) => (
  <ComingSoon title={title} phase={phase} description={description} />
);

// Screen IDs (D-xx, H-xx, E-xx, A-xx, S-xx) refer to SPEC §4.4.
export const router = createBrowserRouter([
  { path: "/", element: <HomePage /> },
  {
    element: <RedirectIfSignedIn />,
    children: [
      {
        element: <AuthLayout />,
        children: [
          { path: "/login", element: <LoginPage /> },
          { path: "/register", element: <RegisterPage /> },
          { path: "/forgot-password", element: <ForgotPasswordPage /> },
        ],
      },
    ],
  },
  { element: <AuthLayout />, children: [{ path: "/verify", element: <VerifyOtpPage /> }] },
  {
    path: "/driver",
    element: (
      <RequireAuth permission="shift.register">
        <DriverLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <DriverHomePage /> },
      { path: "route", element: <RoutePage /> },
      { path: "stops/:stopId", element: <StopPage /> },
      { path: "orders/:orderId", element: <OrderPage /> },
      { path: "orders/:orderId/eta", element: <EtaPage /> },
      { path: "orders/:orderId/done", element: <DonePage /> },
      { path: "incidents", element: <MyIncidentsPage /> },
      { path: "incidents/new", element: <ReportIncidentPage /> },
      { path: "shifts", element: <ShiftsPage /> },
      { path: "profile", element: <ProfilePage /> },
    ],
  },
  {
    path: "/hub",
    element: (
      <RequireAuth permission="hub.dashboard.view">
        <DashboardLayout title="Hub" nav={hubNav} />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <HubDashboardPage /> },
      {
        path: "incidents",
        element: <RequireAuth permission="incident.manage" />,
        children: [
          { index: true, element: <IncidentsOverviewPage /> },
          { path: "list", element: <IncidentListPage /> },
          { path: ":incidentId", element: <IncidentDetailPage /> },
        ],
      },
      { path: "tracking", element: <TrackingPage /> },
      { path: "tracking/:orderId", element: <TrackingPage /> },
      { path: "routes", element: soon("Route planning", "Phase 3", "Optimise and reorder stops (H-02).") },
    ],
  },
  {
    path: "/reports",
    element: (
      <RequireAuth permission="report.view">
        <DashboardLayout title="Reports" nav={reportsNav} />
      </RequireAuth>
    ),
    children: [{ index: true, element: soon("Reports", "Phase 3", "Filters, charts and export (E-01, E-02).") }],
  },
  {
    path: "/admin",
    element: (
      <RequireAuth permission="user.manage">
        <DashboardLayout title="System admin" nav={adminNav} />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <UsersPage /> },
      { path: "users/new", element: <UserFormPage /> },
      { path: "users/:userId", element: <UserFormPage /> },
      {
        path: "roles",
        element: (
          <RequireAuth permission="role.manage">
            <RolesPage />
          </RequireAuth>
        ),
      },
      { path: "hubs", element: soon("Hubs & areas", "Phase 3", "(A-04)") },
      { path: "shifts", element: soon("Shifts", "Phase 3", "Shift times and capacity (A-05).") },
      { path: "settings", element: soon("Settings", "Phase 3", "Dispatch weights, timeouts, SLA (A-06).") },
    ],
  },
  { path: "/shopnow", element: <ShopNowPage /> },
  { path: "/track", element: <TrackPage /> },
  { path: "/track/:waybill", element: <TrackPage /> },
  { path: "*", element: <NotFoundPage /> },
]);
