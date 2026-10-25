// DriverLayout - mobile-first shell of the driver PWA (390px design) with a text tab bar

import { NavLink, Outlet } from "react-router";
import { Logo } from "@/components/Logo";
import { cn } from "@/lib/cn";

const TABS = [
  { to: "/driver", label: "Home", end: true },
  { to: "/driver/orders", label: "Orders" },
  { to: "/driver/shifts", label: "Shifts" },
  { to: "/driver/profile", label: "Profile" },
];

export function DriverLayout() {
  return (
    <div className="mx-auto flex min-h-full max-w-[430px] flex-col bg-neutral-50 shadow-sm">
      <header className="sticky top-0 z-10 flex h-14 items-center border-b border-line bg-white px-4">
        <Logo className="text-base" />
      </header>
      <main className="flex-1 p-4 pb-6">
        <Outlet />
      </main>
      <nav className="sticky bottom-0 grid grid-cols-4 border-t border-line bg-white" aria-label="Driver">
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
    </div>
  );
}
