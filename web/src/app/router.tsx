// Router - public pages, sign-in flow and one guarded area per role (SPEC §4.3).
// Screens behind sign-in are loaded on demand, so the map library and the hub, report and
// admin screens are not part of the first download.

import {
  CalendarClock,
  ChartArea,
  ChartPie,
  Crosshair,
  LayoutGrid,
  ScrollText,
  Send,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Users,
  Warehouse,
} from "lucide-react";
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
import { BackOfficeLayout } from "./layouts/BackOfficeLayout";
import { DriverLayout } from "./layouts/DriverLayout";
import { HubLayout } from "./layouts/HubLayout";
import type { NavItem } from "./layouts/nav";

/** A page module loaded when its route is first opened. */
function page<T extends Record<string, unknown>>(load: () => Promise<T>, name: keyof T & string) {
  const Component = lazy(() => load().then((module) => ({ default: module[name] as ComponentType })));
  return (
    <Suspense fallback={<Loading />}>
      <Component />
    </Suspense>
  );
}

// Icons follow the Figma hub rail: grid, pie, send, target, chart.
const hubNav: NavItem[] = [
  { to: "/hub", label: "Dashboard", icon: LayoutGrid, end: true },
  { to: "/hub/incidents", label: "Incidents", icon: ChartPie, permission: "incident.manage" },
  { to: "/hub/tracking", label: "Delivery tracking", icon: Send, permission: "driver.view_hub" },
  { to: "/hub/routes", label: "Route planning", icon: Crosshair, permission: "route.plan" },
  { to: "/reports", label: "Reports", icon: ChartArea, permission: "report.view" },
];

const reportsNav: NavItem[] = [{ to: "/reports", label: "Dashboard", icon: ChartArea, end: true }];

// Hub managers also read reports; this takes them back to their hub screens.
const reportsSupport: NavItem[] = [
  { to: "/hub", label: "Hub screens", icon: LayoutGrid, permission: "hub.dashboard.view" },
  { to: "/admin/settings", label: "Settings", icon: Settings, permission: "settings.manage" },
];

const adminNav: NavItem[] = [
  { to: "/admin", label: "Users", icon: Users, end: true, permission: "user.manage" },
  { to: "/admin/roles", label: "Roles & permissions", icon: ShieldCheck, permission: "role.manage" },
  { to: "/admin/hubs", label: "Hubs & areas", icon: Warehouse, permission: "hub.manage" },
  { to: "/admin/shifts", label: "Shifts", icon: CalendarClock, permission: "hub.manage" },
  { to: "/admin/settings", label: "Settings", icon: SlidersHorizontal, permission: "settings.manage" },
  { to: "/admin/audit", label: "Audit log", icon: ScrollText, permission: "audit.view" },
];

const adminSupport: NavItem[] = [{ to: "/reports", label: "Reports", icon: ChartArea, permission: "report.view" }];

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
    element: guarded("hub.dashboard.view", <HubLayout nav={hubNav} />),
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
    element: guarded("report.view", <BackOfficeLayout title="Reports" nav={reportsNav} support={reportsSupport} />),
    children: [{ index: true, element: page(() => import("@/features/reports/pages/ReportsPage"), "ReportsPage") }],
  },
  {
    path: "/admin",
    element: guarded("user.manage", <BackOfficeLayout title="System admin" nav={adminNav} support={adminSupport} />),
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
