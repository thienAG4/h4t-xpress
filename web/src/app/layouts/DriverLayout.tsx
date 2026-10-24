import { House, ListChecks, Map, UserRound } from "lucide-react";
import { NavLink, Outlet } from "react-router";
import { Logo } from "@/components/Logo";
import { cn } from "@/lib/cn";

const tabs = [
  { to: "/driver", label: "Home", icon: House, end: true },
  { to: "/driver/route", label: "Route", icon: Map },
  { to: "/driver/orders", label: "Orders", icon: ListChecks },
  { to: "/driver/profile", label: "Profile", icon: UserRound },
];

/** Mobile-first shell for the driver PWA: designed at 390px with a bottom tab bar. */
export function DriverLayout() {
  return (
    <div className="mx-auto flex min-h-full max-w-[430px] flex-col bg-white shadow-sm">
      <header className="flex h-14 items-center border-b border-neutral-200 px-4">
        <Logo className="text-sm" />
      </header>
      <main className="flex-1 p-4">
        <Outlet />
      </main>
      <nav
        className="sticky bottom-0 grid grid-cols-4 border-t border-neutral-200 bg-white"
        aria-label="Driver"
      >
        {tabs.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex flex-col items-center gap-1 py-2 text-xs",
                isActive ? "text-primary-600" : "text-neutral-500",
              )
            }
          >
            <Icon className="size-5" aria-hidden />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
