// HomePage - public landing: what the product does, entry points per role, demo status

import { Link } from "react-router";
import { Logo } from "@/components/Logo";
import { ServerStatus } from "@/features/system/ServerStatus";
import { homePathFor, useSession } from "@/lib/session";

type Entry = {
  to: string;
  title: string;
  role: string;
  description: string;
};

const ENTRIES: Entry[] = [
  {
    to: "/driver",
    title: "Driver app",
    role: "Driver, mobile PWA",
    description: "Register shifts, go online, then accept offers, update status and ETA, report incidents.",
  },
  {
    to: "/hub",
    title: "Hub dashboard",
    role: "Hub Manager",
    description: "Real-time monitoring, incident handling, driver reassignment and rerouting.",
  },
  {
    to: "/reports",
    title: "Reports",
    role: "Executive",
    description: "Success and on-time rates, failure reasons, top drivers and hubs, export to Excel/PDF.",
  },
  {
    to: "/admin",
    title: "System admin",
    role: "System Admin",
    description: "Accounts, the role-permission matrix, hubs, shifts and dispatch settings.",
  },
  {
    to: "/shopnow",
    title: "ShopNow simulator",
    role: "Simulated e-commerce partner",
    description: "Send orders through the partner API and see what the shop is told.",
  },
];

export function HomePage() {
  const { status, user } = useSession();

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <Logo className="text-xl" />
        <div className="flex items-center gap-3">
          <ServerStatus />
          {status === "authenticated" && user ? (
            <Link to={homePathFor(user)} className="text-sm font-semibold text-primary-600">
              Continue as {user.full_name}
            </Link>
          ) : (
            <Link
              to="/login"
              className="inline-flex h-10 items-center rounded-button bg-primary-600 px-4 text-sm font-semibold text-white hover:bg-primary-700"
            >
              Log In
            </Link>
          )}
        </div>
      </header>

      <section className="mt-12 max-w-2xl">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Last-mile delivery, with incidents handled in minutes.
        </h1>
        <p className="mt-4 text-neutral-600">
          Drivers report problems from the road, hub managers reroute or reassign with system suggestions,
          and customers get a new ETA and the reason for the delay through the partner platform.
        </p>
      </section>

      <section className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-label="Apps">
        {ENTRIES.map(({ to, title, role, description }) => (
          <Link
            key={to}
            to={to}
            className="group flex flex-col rounded-card border border-line bg-white p-5 transition hover:border-primary-200 hover:shadow-md"
          >
            <p className="text-xs font-semibold tracking-wide text-primary-700 uppercase">{role}</p>
            <h2 className="mt-2 font-semibold">{title}</h2>
            <p className="mt-2 flex-1 text-sm text-neutral-600">{description}</p>
            <span className="mt-4 text-sm font-semibold text-primary-600 group-hover:underline">Open</span>
          </Link>
        ))}
      </section>
    </div>
  );
}
