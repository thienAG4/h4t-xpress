// DriverHomePage - D-04: today's shift, availability switch and counters

import { Link } from "react-router";
import { Alert, Badge, Card, Loading, Switch } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatDay, formatTime } from "@/lib/format";
import { useSession } from "@/lib/session";
import { useDriverToday, useSetAvailability } from "../hooks";

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
