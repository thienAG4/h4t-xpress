// DriverHomePage - D-04: today's shift, availability switch, current route and counters

import { Link } from "react-router";
import { Alert, Badge, Card, Loading, Switch } from "@/components/ui";
import { useRoute } from "@/features/delivery/hooks";
import { errorMessage } from "@/lib/errors";
import { formatClock, formatDay, formatTime } from "@/lib/format";
import { useSession } from "@/lib/session";
import { useDriverToday, useSetAvailability } from "../hooks";

function CurrentRoute() {
  const route = useRoute();
  if (!route.data) return null;
  const { to_pick_up: toPickUp, ready_to_start: ready, stops } = route.data;
  const next = stops.find((stop) => stop.orders.some((order) => order.status === "OUT_FOR_DELIVERY"));
  return (
    <Card
      title="Current route"
      actions={
        <Link to="/driver/route" className="text-sm font-semibold text-primary-600">
          Open
        </Link>
      }
    >
      {toPickUp.length + ready + stops.length === 0 ? (
        <p className="text-sm text-neutral-600">No orders yet. Offers appear on screen while you are online.</p>
      ) : (
        <dl className="grid grid-cols-3 gap-3 text-center">
          <div>
            <dt className="text-xs text-neutral-600">To pick up</dt>
            <dd className="font-display text-xl font-bold">{toPickUp.length}</dd>
          </div>
          <div>
            <dt className="text-xs text-neutral-600">Scanned</dt>
            <dd className="font-display text-xl font-bold">{ready}</dd>
          </div>
          <div>
            <dt className="text-xs text-neutral-600">Stops</dt>
            <dd className="font-display text-xl font-bold">{stops.length}</dd>
          </div>
        </dl>
      )}
      {next && (
        <p className="mt-3 border-t border-line pt-3 text-sm">
          Next: <span className="font-semibold">{next.recipient_name}</span>, {next.address} at {formatClock(next.eta)}
        </p>
      )}
    </Card>
  );
}

export function DriverHomePage() {
  const user = useSession((state) => state.user);
  const today = useDriverToday();
  const availability = useSetAvailability();

  if (today.isPending) return <Loading />;
  if (today.isError) return <Alert tone="danger">{errorMessage(today.error)}</Alert>;

  const data = today.data;
  const online = data.availability === "ONLINE";
  const hasShiftToday = data.shifts_today.length > 0;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="text-sm text-neutral-600">{formatDay(data.date)}</p>
        <h1 className="text-lg font-bold">Hello, {user?.full_name.split(" ").slice(-1)[0]}</h1>
        {data.hub && <p className="text-sm text-neutral-600">{data.hub.name}</p>}
      </div>

      <Card>
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="font-semibold">Ready for orders</p>
            <p className="text-sm text-neutral-600">
              {online ? "You are online. New offers will appear here." : "Go online to receive offers."}
            </p>
          </div>
          <Switch
            label="Ready for orders"
            checked={online}
            disabled={availability.isPending || (!online && !hasShiftToday)}
            onChange={(checked) => availability.mutate(checked)}
          />
        </div>
        {!hasShiftToday && (
          <Alert tone="warning" className="mt-4">
            You have no shift today.{" "}
            <Link to="/driver/shifts" className="font-semibold underline">
              Register for a shift
            </Link>{" "}
            to go online.
          </Alert>
        )}
      </Card>

      <CurrentRoute />

      <div className="grid grid-cols-2 gap-3">
        <Card className="p-4">
          <p className="text-xs text-neutral-600">Active orders</p>
          <p className="mt-1 font-display text-2xl font-bold">{data.active_orders}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-neutral-600">Delivered today</p>
          <p className="mt-1 font-display text-2xl font-bold">{data.delivered_today}</p>
        </Card>
      </div>

      <Card title="Today's shift">
        {hasShiftToday ? (
          <ul className="flex flex-col gap-2">
            {data.shifts_today.map((shift) => (
              <li key={shift.id} className="flex items-center justify-between">
                <span className="font-medium">{shift.shift_name}</span>
                <Badge tone="primary">
                  {formatTime(shift.start_time)} - {formatTime(shift.end_time)}
                </Badge>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-neutral-600">No shift registered for today.</p>
        )}
      </Card>

      <Card
        title="Upcoming shifts"
        actions={
          <Link to="/driver/shifts" className="text-sm font-semibold text-primary-600">
            Manage
          </Link>
        }
      >
        {data.upcoming.length ? (
          <ul className="flex flex-col gap-2 text-sm">
            {data.upcoming.slice(0, 5).map((shift) => (
              <li key={shift.id} className="flex items-center justify-between">
                <span>{formatDay(shift.work_date)}</span>
                <span className="text-neutral-600">
                  {shift.shift_name}, {formatTime(shift.start_time)} - {formatTime(shift.end_time)}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-neutral-600">No upcoming shifts. Register to get orders.</p>
        )}
      </Card>
    </div>
  );
}
