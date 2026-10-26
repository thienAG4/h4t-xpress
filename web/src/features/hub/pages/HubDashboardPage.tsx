// HubDashboardPage - H-01 laid out like the Figma "HUB Dashboard": recent orders and orders by
// status on top, the order board below, what needs attention on the right, and the two lists
// of orders waiting for a driver and routes in progress at the bottom

import { useSearchParams } from "react-router";
import { Alert, Loading, Panel } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatDay } from "@/lib/format";
import { useSession } from "@/lib/session";
import { AttentionPanel } from "../components/AttentionPanel";
import { RouteProgressPanel, WaitingOrdersPanel } from "../components/DashboardLists";
import { OrdersTable } from "../components/OrdersTable";
import { RecentOrdersPanel } from "../components/RecentOrdersPanel";
import { StatusDonut } from "../components/StatusDonut";
import { useDashboard } from "../hooks";

export function HubDashboardPage() {
  const dashboard = useDashboard();
  const user = useSession((state) => state.user);
  const [params] = useSearchParams();
  const query = params.get("q") ?? "";
  const atRisk = params.get("risk") === "1";

  if (dashboard.isPending) return <Loading />;
  if (dashboard.isError) return <Alert tone="danger">{errorMessage(dashboard.error)}</Alert>;
  const data = dashboard.data;
  const onTime = data.on_time_rate_today === null ? "-" : `${Math.round(data.on_time_rate_today * 100)}%`;

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(300px,360px)]">
      <h1 className="sr-only">Hub dashboard, {formatDay(data.date)}</h1>
      <RecentOrdersPanel dashboard={data} className="xl:col-start-1 xl:row-start-1" />
      <Panel
        title="Orders by status"
        action={
          <span className="text-sm text-neutral-500">
            {data.drivers_online} drivers online - on time {onTime}
          </span>
        }
        className="xl:col-start-2 xl:row-start-1"
        bodyClassName="flex items-center"
      >
        <StatusDonut byStatus={data.by_status} total={data.total} />
      </Panel>
      <AttentionPanel className="xl:col-start-3 xl:row-span-3 xl:row-start-1" />
      {/* Re-created when the top bar search changes, so the board starts from that search. */}
      <OrdersTable key={`${query}|${atRisk}`} query={query} atRisk={atRisk} className="xl:col-span-2 xl:row-start-2" />
      <div className="grid gap-5 lg:grid-cols-2 xl:col-span-2 xl:row-start-3">
        <WaitingOrdersPanel hubName={user?.hub_name ?? "Hub"} />
        <RouteProgressPanel />
      </div>
    </div>
  );
}
