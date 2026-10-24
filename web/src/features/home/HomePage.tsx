import {
  ArrowRight,
  BarChart3,
  LayoutDashboard,
  Settings2,
  ShoppingBag,
  Smartphone,
  type LucideIcon,
} from "lucide-react";
import { Link } from "react-router";
import { Logo } from "@/components/Logo";
import { ServerStatus } from "@/features/system/ServerStatus";

type AppCard = {
  to: string;
  title: string;
  role: string;
  description: string;
  icon: LucideIcon;
};

const apps: AppCard[] = [
  {
    to: "/driver",
    title: "Driver app",
    role: "Driver · mobile PWA",
    description: "Accept offers, scan waybills, update status and ETA, report incidents.",
    icon: Smartphone,
  },
  {
    to: "/hub",
    title: "Hub dashboard",
    role: "Hub Manager",
    description: "Real-time monitoring, incident handling, driver reassignment and rerouting.",
    icon: LayoutDashboard,
  },
  {
    to: "/reports",
    title: "Reports",
    role: "Executive",
    description: "Success and on-time rates, failure reasons, top drivers and hubs, export.",
    icon: BarChart3,
  },
  {
    to: "/admin",
    title: "System admin",
    role: "System Admin",
    description: "Accounts, role-permission matrix, hubs, shifts and dispatch settings.",
    icon: Settings2,
  },
  {
    to: "/shopnow",
    title: "ShopNow simulator",
    role: "Simulated e-commerce partner",
    description: "Send orders through the partner API and see what customers are told.",
    icon: ShoppingBag,
  },
];

export function HomePage() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <Logo className="text-xl" />
        <ServerStatus />
      </header>

      <section className="mt-12 max-w-2xl">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Last-mile delivery, with incidents handled in minutes.
        </h1>
        <p className="mt-4 text-neutral-600">
          Drivers report problems from the road, hub managers reroute or reassign with system
          suggestions, and customers get a new ETA and the reason for the delay through the
          partner platform.
        </p>
      </section>

      <section className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-label="Apps">
        {apps.map(({ to, title, role, description, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            className="group flex flex-col rounded-card border border-neutral-200 bg-white p-5 transition hover:border-primary-200 hover:shadow-md"
          >
            <span className="grid size-10 place-items-center rounded-control bg-primary-50 text-primary-600">
              <Icon className="size-5" aria-hidden />
            </span>
            <h2 className="mt-4 font-semibold">{title}</h2>
            <p className="text-xs font-medium text-primary-700">{role}</p>
            <p className="mt-2 flex-1 text-sm text-neutral-600">{description}</p>
            <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-primary-600">
              Open
              <ArrowRight className="size-4 transition group-hover:translate-x-0.5" aria-hidden />
            </span>
          </Link>
        ))}
      </section>
    </div>
  );
}
