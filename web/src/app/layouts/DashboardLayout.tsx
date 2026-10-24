import type { LucideIcon } from "lucide-react";
import { NavLink, Outlet } from "react-router";
import { Logo } from "@/components/Logo";
import { ServerStatus } from "@/features/system/ServerStatus";
import { cn } from "@/lib/cn";

export type NavItem = {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
};

type Props = {
  title: string;
  nav: NavItem[];
};

/** Desktop shell for Hub, Reports and Admin: sidebar + top bar (Figma Hub/Admin pages). */
export function DashboardLayout({ title, nav }: Props) {
  return (
    <div className="flex min-h-full">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-neutral-200 bg-white px-4 py-5 md:flex">
        <NavLink to="/" className="px-2">
          <Logo />
        </NavLink>
        <nav className="mt-8 flex flex-col gap-1" aria-label={title}>
          {nav.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-control px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary-50 text-primary-700"
                    : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900",
                )
              }
            >
              <Icon className="size-4" aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-neutral-200 bg-white px-6">
          <h1 className="text-lg font-semibold">{title}</h1>
          <ServerStatus />
        </header>
        <nav
          className="flex gap-2 overflow-x-auto border-b border-neutral-200 bg-white px-4 py-2 md:hidden"
          aria-label={`${title} (mobile)`}
        >
          {nav.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "shrink-0 rounded-full px-3 py-1 text-sm",
                  isActive ? "bg-primary-600 text-white" : "bg-neutral-100 text-neutral-700",
                )
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
