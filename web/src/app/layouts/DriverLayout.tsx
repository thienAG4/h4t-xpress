// DriverLayout - mobile-first shell of the driver PWA (390px design) with a text tab bar.
// While the driver is online it sends the presence heartbeat and shows incoming offers.

import { NavLink, Outlet } from "react-router";
import { Logo } from "@/components/Logo";
import { OfferModal } from "@/features/delivery/components/OfferModal";
import { useHeartbeat } from "@/features/delivery/hooks";
import { useDriverToday } from "@/features/driver/hooks";
import { cn } from "@/lib/cn";

const TABS = [
  { to: "/driver", label: "Home", end: true },
  { to: "/driver/route", label: "Route" },
  { to: "/driver/incidents", label: "Issues" },
  { to: "/driver/shifts", label: "Shifts" },
  { to: "/driver/profile", label: "Profile" },
];

export function DriverLayout() {
  const today = useDriverToday();
  const online = today.data?.availability === "ONLINE";
  useHeartbeat(online, today.data?.hub ?? null);

  return (
    <div className="mx-auto flex min-h-full max-w-[430px] flex-col bg-neutral-50 shadow-sm">
      <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-line bg-white px-4">
        <Logo className="text-base" />
        {today.data && (
          <span className={cn("text-xs font-semibold", online ? "text-success-700" : "text-neutral-500")}>
            {online ? "Online" : "Offline"}
          </span>
        )}
      </header>
      <main className="flex-1 p-4 pb-6">
        <Outlet />
      </main>
      <nav className="sticky bottom-0 z-20 grid grid-cols-5 border-t border-line bg-white" aria-label="Driver">
        {TABS.map(({ to, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "py-3 text-center text-sm font-medium",
                isActive ? "border-t-2 border-primary-600 text-primary-600" : "border-t-2 border-transparent text-neutral-500",
              )
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
      <OfferModal enabled={online} />
    </div>
  );
}
