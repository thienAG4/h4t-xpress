// DashboardLayout - desktop shell for Hub, Reports and Admin: sidebar, top bar, user menu

import { useMutation } from "@tanstack/react-query";
import { NavLink, Outlet, useNavigate } from "react-router";
import { Logo } from "@/components/Logo";
import { Button } from "@/components/ui";
import { logout } from "@/features/auth/api";
import { ServerStatus } from "@/features/system/ServerStatus";
import { cn } from "@/lib/cn";
import { hasPermission, useSession } from "@/lib/session";

export type NavItem = {
  to: string;
  label: string;
  end?: boolean;
  // The link is only shown to users holding this permission (menus follow RBAC).
  permission?: string;
};

type Props = {
  title: string;
  nav: NavItem[];
};

export function DashboardLayout({ title, nav }: Props) {
  const navigate = useNavigate();
  const user = useSession((state) => state.user);
  const items = nav.filter((item) => !item.permission || hasPermission(user, item.permission));
  const signOut = useMutation({
    mutationFn: logout,
    onSettled: () => navigate("/login", { replace: true }),
  });

  return (
    <div className="flex min-h-full">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-line bg-white px-4 py-5 md:flex">
        <NavLink to="/" className="px-2">
          <Logo />
        </NavLink>
        <p className="mt-6 px-3 text-xs font-semibold tracking-wide text-neutral-500 uppercase">{title}</p>
        <nav className="mt-2 flex flex-col gap-1" aria-label={title}>
          {items.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "rounded-input px-3 py-2 text-sm font-medium transition-colors",
                  isActive ? "bg-primary-50 text-primary-700" : "text-neutral-600 hover:bg-neutral-100 hover:text-ink",
                )
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        {user && (
          <div className="mt-auto border-t border-line px-2 pt-4">
            <p className="truncate text-sm font-semibold">{user.full_name}</p>
            <p className="truncate text-xs text-neutral-600">{user.role_name}</p>
            <Button
              variant="link"
              className="mt-2"
              loading={signOut.isPending}
              onClick={() => signOut.mutate()}
            >
              Sign out
            </Button>
          </div>
        )}
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between gap-4 border-b border-line bg-white px-6">
          <span className="font-display text-base font-semibold md:hidden">
            <Logo className="text-base" />
          </span>
          <span className="hidden text-sm text-neutral-600 md:block">{user?.hub_name ?? "All hubs"}</span>
          <div className="flex items-center gap-3">
            <ServerStatus />
            <Button variant="secondary" size="sm" className="md:hidden" onClick={() => signOut.mutate()}>
              Sign out
            </Button>
          </div>
        </header>
        <nav
          className="flex gap-2 overflow-x-auto border-b border-line bg-white px-4 py-2 md:hidden"
          aria-label={`${title} (mobile)`}
        >
          {items.map(({ to, label, end }) => (
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
