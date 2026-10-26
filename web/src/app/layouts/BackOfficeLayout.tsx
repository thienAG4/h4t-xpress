// BackOfficeLayout - Figma "Nhà quản trị" shell for Reports and System Admin: wide sidebar with
// labelled icons, a support section and the signed-in user at the bottom

import { LogOut } from "lucide-react";
import { NavLink, Outlet } from "react-router";
import { Wordmark } from "@/components/Logo";
import { Avatar } from "@/components/ui";
import { ServerStatus } from "@/features/system/ServerStatus";
import { cn } from "@/lib/cn";
import { useSession } from "@/lib/session";
import { useSignOut, useVisibleNav, type NavItem } from "./nav";

function SideLink({ item }: { item: NavItem }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.end}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-medium transition-colors",
          isActive ? "bg-primary-50 text-primary-600" : "text-neutral-700 hover:bg-neutral-50 hover:text-ink",
        )
      }
    >
      <Icon className="size-[18px]" strokeWidth={1.9} aria-hidden />
      {item.label}
    </NavLink>
  );
}

export function BackOfficeLayout({ title, nav, support = [] }: { title: string; nav: NavItem[]; support?: NavItem[] }) {
  const user = useSession((state) => state.user);
  const items = useVisibleNav(nav);
  const extras = useVisibleNav(support);
  const signOut = useSignOut();

  return (
    <div className="flex min-h-full bg-canvas">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-line bg-white px-5 py-8 md:flex">
        <NavLink to="/" className="px-3.5">
          <Wordmark />
        </NavLink>
        <nav className="mt-8 flex flex-col gap-1.5" aria-label={title}>
          {items.map((item) => (
            <SideLink key={item.to} item={item} />
          ))}
        </nav>
        {extras.length > 0 && (
          <>
            <p className="mt-8 px-3.5 text-sm text-neutral-500">Support</p>
            <nav className="mt-2 flex flex-col gap-1.5" aria-label="Support">
              {extras.map((item) => (
                <SideLink key={item.to} item={item} />
              ))}
            </nav>
          </>
        )}
        {user && (
          <div className="mt-auto flex flex-col gap-3 border-t border-line pt-5">
            <ServerStatus className="self-start" />
            <div className="flex items-center gap-3">
              <Avatar name={user.full_name} />
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">{user.full_name}</p>
                <p className="truncate text-xs text-neutral-500">{user.email}</p>
              </div>
            </div>
            <button
              type="button"
              className="flex items-center gap-2 self-start text-sm font-medium text-neutral-600 hover:text-danger-700"
              onClick={() => signOut.mutate()}
              disabled={signOut.isPending}
            >
              <LogOut className="size-4" aria-hidden />
              Sign out
            </button>
          </div>
        )}
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-line bg-white px-4 py-3 md:hidden">
          <Wordmark />
          <button type="button" className="text-sm font-medium text-neutral-700" onClick={() => signOut.mutate()}>
            Sign out
          </button>
        </header>
        <nav className="flex gap-2 overflow-x-auto border-b border-line bg-white px-4 py-2 md:hidden" aria-label={`${title} (mobile)`}>
          {[...items, ...extras].map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn("shrink-0 rounded-full px-3 py-1 text-sm", isActive ? "bg-primary-600 text-white" : "bg-neutral-100 text-neutral-700")
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <main className="min-w-0 flex-1 px-5 py-6 md:px-8 md:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
