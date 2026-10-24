import {
  AlertTriangle,
  BarChart3,
  Building2,
  CalendarClock,
  LayoutDashboard,
  MapPinned,
  Route,
  ShieldCheck,
  SlidersHorizontal,
  Users,
} from "lucide-react";
import { createBrowserRouter } from "react-router";
import { ComingSoon } from "@/components/ComingSoon";
import { HomePage } from "@/features/home/HomePage";
import { NotFoundPage } from "@/features/home/NotFoundPage";
import { DashboardLayout, type NavItem } from "./layouts/DashboardLayout";
import { DriverLayout } from "./layouts/DriverLayout";

const hubNav: NavItem[] = [
  { to: "/hub", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/hub/routes", label: "Route planning", icon: Route },
  { to: "/hub/tracking", label: "Delivery tracking", icon: MapPinned },
  { to: "/hub/incidents", label: "Incidents", icon: AlertTriangle },
];

const reportsNav: NavItem[] = [{ to: "/reports", label: "Reports", icon: BarChart3, end: true }];

const adminNav: NavItem[] = [
  { to: "/admin", label: "Users", icon: Users, end: true },
  { to: "/admin/roles", label: "Roles & permissions", icon: ShieldCheck },
  { to: "/admin/hubs", label: "Hubs & areas", icon: Building2 },
  { to: "/admin/shifts", label: "Shifts", icon: CalendarClock },
  { to: "/admin/settings", label: "Settings", icon: SlidersHorizontal },
];

const soon = (title: string, phase: string, description?: string) => (
  <ComingSoon title={title} phase={phase} description={description} />
);

// Screen IDs (D-xx, H-xx, E-xx, A-xx, S-xx) refer to SPEC §4.4.
export const router = createBrowserRouter([
  { path: "/", element: <HomePage /> },
  {
    path: "/login",
    element: (
      <div className="mx-auto max-w-md p-6">
        {soon("Sign in", "Phase 1", "Email or phone + password, with quick demo login per role.")}
      </div>
    ),
  },
  {
    path: "/driver",
    element: <DriverLayout />,
    children: [
      { index: true, element: soon("Driver home", "Phase 1", "Today's shift and availability (D-04).") },
      { path: "route", element: soon("Today's route", "Phase 2", "Map and stop list (D-07).") },
      { path: "orders", element: soon("My orders", "Phase 2", "Order detail and status (D-08).") },
      { path: "profile", element: soon("Profile", "Phase 2", "Profile and password (D-15).") },
    ],
  },
  {
    path: "/hub",
    element: <DashboardLayout title="Hub" nav={hubNav} />,
    children: [
      { index: true, element: soon("Hub dashboard", "Phase 2", "KPIs, order table, alerts (H-01).") },
      { path: "routes", element: soon("Route planning", "Phase 3", "Optimise and reorder (H-02).") },
      { path: "tracking", element: soon("Delivery tracking", "Phase 2", "Live map (H-03).") },
      { path: "incidents", element: soon("Incidents", "Phase 2", "Classify and resolve (H-04..H-08).") },
    ],
  },
  {
    path: "/reports",
    element: <DashboardLayout title="Reports" nav={reportsNav} />,
    children: [
      { index: true, element: soon("Reports", "Phase 3", "Filters, charts and export (E-01, E-02).") },
    ],
  },
  {
    path: "/admin",
    element: <DashboardLayout title="System admin" nav={adminNav} />,
    children: [
      { index: true, element: soon("Users", "Phase 1", "Create, edit, lock accounts (A-01, A-02).") },
      { path: "roles", element: soon("Roles & permissions", "Phase 1", "Permission matrix (A-03).") },
      { path: "hubs", element: soon("Hubs & areas", "Phase 3", "(A-04)") },
      { path: "shifts", element: soon("Shifts", "Phase 3", "(A-05)") },
      { path: "settings", element: soon("Settings", "Phase 3", "Dispatch, ETA, SLA (A-06).") },
    ],
  },
  {
    path: "/shopnow",
    element: (
      <div className="mx-auto max-w-3xl p-6">
        {soon("ShopNow simulator", "Phase 1", "Create orders through the partner API (S-01, S-02).")}
      </div>
    ),
  },
  {
    path: "/track/:waybill",
    element: (
      <div className="mx-auto max-w-md p-6">
        {soon("Track your parcel", "Phase 2", "Customer view from ShopNow webhooks (S-03).")}
      </div>
    ),
  },
  { path: "*", element: <NotFoundPage /> },
]);
