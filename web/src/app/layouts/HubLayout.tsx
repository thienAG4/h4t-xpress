// HubLayout - Figma hub shell: narrow icon rail on the left, top bar with search, quick actions,
// open incidents and the user menu

import { Bell, ChevronDown, CircleAlert, Funnel, LogOut, Plus, Search } from "lucide-react";
import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router";
import { LogoMark } from "@/components/Logo";
import { Avatar, IconTile, Popover } from "@/components/ui";
import { useIncidentList } from "@/features/incidents/hooks";
import { ServerStatus } from "@/features/system/ServerStatus";
import { cn } from "@/lib/cn";
import { formatRelative } from "@/lib/format";
import { INCIDENT_TYPE } from "@/lib/labels";
import { useSession } from "@/lib/session";
import { useSignOut, useVisibleNav, type NavItem } from "./nav";

const ICON_BUTTON =
  "grid size-10 place-items-center rounded-lg border border-line bg-white text-neutral-700 hover:border-primary-200 hover:text-primary-600";

function RailLink({ item }: { item: NavItem }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.end}
      aria-label={item.label}
      className={({ isActive }) =>
        cn(
          "group relative grid size-11 place-items-center rounded-full transition-colors",
          isActive ? "bg-primary-50 text-primary-600" : "text-neutral-500 hover:bg-neutral-100 hover:text-ink",
        )
      }
    >
      <Icon className="size-[22px]" strokeWidth={1.6} aria-hidden />
      {/* Icon-only rail: the label appears beside the icon on hover and keyboard focus. */}
      <span className="pointer-events-none absolute left-full z-[1100] ml-3 rounded-md bg-ink px-2 py-1 text-xs whitespace-nowrap text-white opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
        {item.label}
      </span>
    </NavLink>
  );
}

function SearchBox() {
  const navigate = useNavigate();
  const [text, setText] = useState("");
  return (
    <form
      role="search"
      className="relative hidden w-full max-w-sm sm:block"
      onSubmit={(event) => {
        event.preventDefault();
        const q = text.trim();
        navigate(q ? `/hub?q=${encodeURIComponent(q)}` : "/hub");
      }}
    >
      <Search className="absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-neutral-400" aria-hidden />
      <input
        type="search"
        aria-label="Search orders"
        placeholder="Search by waybill, customer or phone"
        value={text}
        onChange={(event) => setText(event.target.value)}
        className="h-10 w-full rounded-lg border border-line bg-white pr-3 pl-10 text-sm placeholder:text-placeholder focus:border-primary-500 focus:outline-none"
      />
    </form>
  );
}

function QuickActions({ items }: { items: NavItem[] }) {
  const actions = items.filter((item) => item.to !== "/hub");
  return (
    <Popover
      label="Quick actions"
      buttonClassName="grid size-10 place-items-center rounded-lg border border-primary-500 bg-primary-50 text-primary-600 hover:bg-primary-100"
      button={<Plus className="size-5" aria-hidden />}
      panelClassName="w-[22rem] p-3"
    >
      {(close) => (
        <div className="grid grid-cols-2 gap-3">
          {actions.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              onClick={close}
              className="flex flex-col items-center gap-2 rounded-lg border border-line px-3 py-4 text-center hover:border-primary-200 hover:bg-primary-50/40"
            >
              <IconTile icon={item.icon} size="lg" />
              <span className="text-xs font-semibold tracking-wide text-ink uppercase">{item.label}</span>
            </Link>
          ))}
        </div>
      )}
    </Popover>
  );
}

function OpenIncidents() {
  const incidents = useIncidentList({ page: 1, page_size: 5, open_only: true });
  const total = incidents.data?.total ?? 0;
  return (
    <Popover
      label={`Open incidents: ${total}`}
      buttonClassName={cn(ICON_BUTTON, "relative")}
      button={
        <>
          <Bell className="size-5" strokeWidth={1.75} aria-hidden />
          {total > 0 && (
            <span className="absolute -top-1.5 -right-1.5 grid min-w-5 place-items-center rounded-full bg-danger-500 px-1 text-[11px] font-semibold text-white">
              {total}
            </span>
          )}
        </>
      }
      panelClassName="w-80"
    >
      {(close) => (
        <div>
          <p className="border-b border-line px-4 py-3 text-sm font-semibold">Open incidents</p>
          {total === 0 && <p className="px-4 py-6 text-center text-sm text-neutral-600">Nothing needs your attention.</p>}
          <ul>
            {incidents.data?.items.map((incident) => (
              <li key={incident.id}>
                <Link
                  to={`/hub/incidents/${incident.id}`}
                  onClick={close}
                  className="flex gap-3 border-b border-line px-4 py-3 hover:bg-neutral-50"
                >
                  <IconTile icon={CircleAlert} tone={incident.priority === "HIGH" ? "danger" : "warning"} size="sm" />
                  <span className="min-w-0 text-sm">
                    <span className="font-semibold">{incident.code}</span> {INCIDENT_TYPE[incident.type]}
                    <span className="block truncate text-xs text-neutral-600">
                      {incident.driver_name} - {formatRelative(incident.reported_at)}
                    </span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
          <Link
            to="/hub/incidents/list?open=1"
            onClick={close}
            className="block px-4 py-3 text-center text-sm font-medium text-primary-600 hover:underline"
          >
            View all incidents
          </Link>
        </div>
      )}
    </Popover>
  );
}

function UserMenu() {
  const user = useSession((state) => state.user);
  const signOut = useSignOut();
  if (!user) return null;
  return (
    <Popover
      label="Account"
      buttonClassName="flex items-center gap-3 rounded-lg py-1 pr-1 pl-1 text-left hover:bg-neutral-50"
      button={
        <>
          <Avatar name={user.full_name} shape="square" size="lg" />
          <span className="hidden md:block">
            <span className="block text-sm font-semibold text-ink">{user.full_name}</span>
            <span className="block text-xs text-neutral-600">{user.role_name}</span>
          </span>
          <ChevronDown className="ml-2 size-4 text-neutral-500" aria-hidden />
        </>
      }
      panelClassName="w-72 p-4"
    >
      {() => (
        <div className="flex flex-col gap-3 text-sm">
          <div>
            <p className="font-semibold">{user.full_name}</p>
            <p className="text-neutral-600">{user.email}</p>
            <p className="mt-1 text-neutral-600">{user.hub_name ?? "All hubs"}</p>
          </div>
          <ServerStatus className="self-start" />
          <button
            type="button"
            className="flex items-center gap-2 border-t border-line pt-3 font-medium text-danger-700 hover:underline"
            onClick={() => signOut.mutate()}
            disabled={signOut.isPending}
          >
            <LogOut className="size-4" aria-hidden />
            Sign out
          </button>
        </div>
      )}
    </Popover>
  );
}

export function HubLayout({ nav }: { nav: NavItem[] }) {
  const items = useVisibleNav(nav);
  const signOut = useSignOut();

  return (
    <div className="flex min-h-full bg-canvas">
      <aside className="sticky top-0 hidden h-screen w-[84px] shrink-0 flex-col items-center border-r border-line bg-white py-5 md:flex">
        <NavLink to="/hub" aria-label="H4T Xpress hub home">
          <LogoMark />
        </NavLink>
        <nav className="mt-9 flex flex-col items-center gap-4" aria-label="Hub">
          {items.map((item) => (
            <RailLink key={item.to} item={item} />
          ))}
        </nav>
        <div className="my-6 h-px w-14 bg-line" />
        <button
          type="button"
          aria-label="Sign out"
          title="Sign out"
          className="grid size-11 place-items-center rounded-full text-neutral-500 hover:bg-danger-50 hover:text-danger-700"
          onClick={() => signOut.mutate()}
        >
          <LogOut className="size-[22px]" strokeWidth={1.6} aria-hidden />
        </button>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-[1050] flex h-[72px] items-center justify-between gap-4 border-b border-line bg-white px-5">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <NavLink to="/hub" className="md:hidden" aria-label="H4T Xpress hub home">
              <LogoMark />
            </NavLink>
            <SearchBox />
            <Link to="/hub?risk=1" aria-label="Orders at SLA risk" title="Orders at SLA risk" className={ICON_BUTTON}>
              <Funnel className="size-5" strokeWidth={1.75} aria-hidden />
            </Link>
          </div>
          <div className="flex items-center gap-3">
            <QuickActions items={items} />
            <OpenIncidents />
            <UserMenu />
          </div>
        </header>
        <nav className="flex gap-2 overflow-x-auto border-b border-line bg-white px-4 py-2 md:hidden" aria-label="Hub (mobile)">
          {items.map(({ to, label, end }) => (
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
        <main className="min-w-0 flex-1 p-5">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
