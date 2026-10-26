// Router - public pages, sign-in flow and one guarded area per role (SPEC §4.3).
// Screens behind sign-in are loaded on demand, so the map library and the hub, report and
// admin screens are not part of the first download.

import { lazy, Suspense, type ComponentType, type ReactNode } from "react";
import { createBrowserRouter } from "react-router";
import { Loading } from "@/components/ui";
import { ForgotPasswordPage } from "@/features/auth/pages/ForgotPasswordPage";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { RegisterPage } from "@/features/auth/pages/RegisterPage";
import { VerifyOtpPage } from "@/features/auth/pages/VerifyOtpPage";
import { DriverHomePage } from "@/features/driver/pages/DriverHomePage";
import { HomePage } from "@/features/home/HomePage";
import { NotFoundPage } from "@/features/home/NotFoundPage";
import { RedirectIfSignedIn, RequireAuth } from "./guards";
import { AuthLayout } from "./layouts/AuthLayout";
import { DashboardLayout, type NavItem } from "./layouts/DashboardLayout";
import { DriverLayout } from "./layouts/DriverLayout";

/** A page module loaded when its route is first opened. */
function page<T extends Record<string, unknown>>(load: () => Promise<T>, name: keyof T & string) {
  const Component = lazy(() => load().then((module) => ({ default: module[name] as ComponentType })));
  return (
    <Suspense fallback={<Loading />}>
      <Component />
    </Suspense>
  );
}

const hubNav: NavItem[] = [
  { to: "/hub", label: "Dashboard", end: true },
  { to: "/hub/incidents", label: "Incidents", permission: "incident.manage" },
  { to: "/hub/tracking", label: "Delivery tracking", permission: "driver.view_hub" },
  { to: "/hub/routes", label: "Route planning", permission: "route.plan" },
  { to: "/reports", label: "Reports", permission: "report.view" },
];

const reportsNav: NavItem[] = [
  { to: "/reports", label: "Overview", end: true },
  // Hub managers also read reports; this takes them back to their hub screens.
  { to: "/hub", label: "Back to hub", permission: "hub.dashboard.view" },
];

const adminNav: NavItem[] = [
  { to: "/admin", label: "Users", end: true, permission: "user.manage" },
  { to: "/admin/roles", label: "Roles & permissions", permission: "role.manage" },
  { to: "/admin/hubs", label: "Hubs & areas", permission: "hub.manage" },
  { to: "/admin/shifts", label: "Shifts", permission: "hub.manage" },
  { to: "/admin/settings", label: "Settings", permission: "settings.manage" },
  { to: "/admin/audit", label: "Audit log", permission: "audit.view" },
];

const guarded = (permission: string, element: ReactNode) => (
  <RequireAuth permission={permission}>{element}</RequireAuth>
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
    element: guarded("shift.register", <DriverLayout />),
    children: [
      { index: true, element: <DriverHomePage /> },
      { path: "route", element: page(() => import("@/features/delivery/pages/RoutePage"), "RoutePage") },
      { path: "stops/:stopId", element: page(() => import("@/features/delivery/pages/StopPage"), "StopPage") },
      { path: "orders/:orderId", element: page(() => import("@/features/delivery/pages/OrderPage"), "OrderPage") },
      { path: "orders/:orderId/eta", element: page(() => import("@/features/delivery/pages/EtaPage"), "EtaPage") },
      { path: "orders/:orderId/done", element: page(() => import("@/features/delivery/pages/DonePage"), "DonePage") },
      {
        path: "incidents",
        element: page(() => import("@/features/incidents/pages/MyIncidentsPage"), "MyIncidentsPage"),
      },
      {
        path: "incidents/new",
        element: page(() => import("@/features/incidents/pages/ReportIncidentPage"), "ReportIncidentPage"),
      },
      { path: "shifts", element: page(() => import("@/features/driver/pages/ShiftsPage"), "ShiftsPage") },
      { path: "profile", element: page(() => import("@/features/driver/pages/ProfilePage"), "ProfilePage") },
    ],
  },
  {
    path: "/hub",
    element: guarded("hub.dashboard.view", <DashboardLayout title="Hub" nav={hubNav} />),
    children: [
      { index: true, element: page(() => import("@/features/hub/pages/HubDashboardPage"), "HubDashboardPage") },
      {
        path: "incidents",
        element: <RequireAuth permission="incident.manage" />,
        children: [
          {
            index: true,
            element: page(() => import("@/features/incidents/pages/IncidentsOverviewPage"), "IncidentsOverviewPage"),
          },
          {
            path: "list",
            element: page(() => import("@/features/incidents/pages/IncidentListPage"), "IncidentListPage"),
          },
          {
            path: ":incidentId",
            element: page(() => import("@/features/incidents/pages/IncidentDetailPage"), "IncidentDetailPage"),
          },
        ],
      },
      {
        path: "tracking",
        element: guarded("driver.view_hub", page(() => import("@/features/hub/pages/TrackingPage"), "TrackingPage")),
      },
      {
        path: "tracking/:orderId",
        element: guarded("driver.view_hub", page(() => import("@/features/hub/pages/TrackingPage"), "TrackingPage")),
      },
      {
        path: "routes",
        element: guarded("route.plan", page(() => import("@/features/hub/pages/RoutePlanningPage"), "RoutePlanningPage")),
      },
    ],
  },
  {
    path: "/reports",
    element: guarded("report.view", <DashboardLayout title="Reports" nav={reportsNav} />),
    children: [{ index: true, element: page(() => import("@/features/reports/pages/ReportsPage"), "ReportsPage") }],
  },
  {
    path: "/admin",
    element: guarded("user.manage", <DashboardLayout title="System admin" nav={adminNav} />),
    children: [
      { index: true, element: page(() => import("@/features/admin/pages/UsersPage"), "UsersPage") },
      { path: "users/new", element: page(() => import("@/features/admin/pages/UserFormPage"), "UserFormPage") },
      { path: "users/:userId", element: page(() => import("@/features/admin/pages/UserFormPage"), "UserFormPage") },
      {
        path: "roles",
        element: guarded("role.manage", page(() => import("@/features/admin/pages/RolesPage"), "RolesPage")),
      },
      {
        path: "hubs",
        element: guarded("hub.manage", page(() => import("@/features/admin/pages/HubsPage"), "HubsPage")),
      },
      {
        path: "shifts",
        element: guarded("hub.manage", page(() => import("@/features/admin/pages/ShiftsPage"), "ShiftsPage")),
      },
      {
        path: "settings",
        element: guarded("settings.manage", page(() => import("@/features/admin/pages/SettingsPage"), "SettingsPage")),
      },
      {
        path: "audit",
        element: guarded("audit.view", page(() => import("@/features/admin/pages/AuditPage"), "AuditPage")),
      },
    ],
  },
  { path: "/shopnow", element: page(() => import("@/features/shopnow/pages/ShopNowPage"), "ShopNowPage") },
  { path: "/shopnow/demo", element: page(() => import("@/features/shopnow/pages/DemoPage"), "DemoPage") },
  { path: "/track", element: page(() => import("@/features/shopnow/pages/TrackPage"), "TrackPage") },
  { path: "/track/:waybill", element: page(() => import("@/features/shopnow/pages/TrackPage"), "TrackPage") },
  { path: "*", element: <NotFoundPage /> },
]);
