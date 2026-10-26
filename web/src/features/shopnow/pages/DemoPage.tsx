// DemoPage - S-04: switch the GPS simulator, stage a traffic jam (raises DRIVER_IDLE after a
// few minutes, BR12) and, for the system admin, reload the demo data.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { Alert, Badge, Button, Card, Dialog, EmptyState, Loading, Switch } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatClock } from "@/lib/format";
import { hasPermission, useSession } from "@/lib/session";
import { toast } from "@/lib/toast";
import { fetchDemoStatus, resetDemo, startTrafficJam, switchGps } from "../api";

const KEY = ["shopnow", "demo"];

export function DemoPage() {
  const queryClient = useQueryClient();
  const user = useSession((state) => state.user);
  const canReset = hasPermission(user, "settings.manage");
  const [confirmReset, setConfirmReset] = useState(false);
  const status = useQuery({ queryKey: KEY, queryFn: fetchDemoStatus, refetchInterval: 5_000 });

  const update = (data: Awaited<ReturnType<typeof fetchDemoStatus>>) => queryClient.setQueryData(KEY, data);
  const gps = useMutation({ mutationFn: switchGps, onSuccess: update, onError: (e) => toast.error(errorMessage(e)) });
  const jam = useMutation({
    mutationFn: startTrafficJam,
    onSuccess: (data) => {
      update(data);
      toast.info(`Driver stopped. The hub gets a "Driver not moving" incident after about ${data.idle_minutes} minutes.`);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const reset = useMutation({
    mutationFn: resetDemo,
    onSuccess: ({ rows }) => {
      setConfirmReset(false);
      toast.success(`Demo data reloaded (${rows.toLocaleString("en-US")} rows). Please sign in again.`);
      window.setTimeout(() => window.location.assign("/login"), 1500);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  return (
    <div className="min-h-full bg-shop-50/40">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-4">
          <Link to="/shopnow" className="font-display text-xl font-extrabold text-shop-600">
            ShopNow
          </Link>
          <span className="text-xs text-neutral-600">Demo controls</span>
        </div>
      </header>
      <main className="mx-auto flex max-w-4xl flex-col gap-6 px-4 py-6">
        {status.isPending && <Loading />}
        {status.isError && <Alert tone="danger">{errorMessage(status.error)}</Alert>}
        {status.data && (
          <>
            <Card title="GPS simulator">
              <div className="flex items-center justify-between gap-4">
                <p className="text-sm text-neutral-700">
                  Drivers already on the road follow real roads at {status.data.speed_factor} times normal speed and
                  deliver with a placeholder photo. The shared accounts driver1 and driver2, and anyone using the app,
                  are never moved by the simulator.
                </p>
                <Switch
                  label="GPS simulator"
                  checked={status.data.gps_enabled}
                  disabled={gps.isPending}
                  onChange={(enabled) => gps.mutate(enabled)}
                />
              </div>
            </Card>

            <Card title={`Simulated drivers (${status.data.drivers.length})`}>
              {status.data.drivers.length === 0 ? (
                <EmptyState title="Nobody is on the road">
                  Simulated drivers finished their routes. A data reload brings new ones.
                </EmptyState>
              ) : (
                <ul className="flex flex-col divide-y divide-line">
                  {status.data.drivers.map((driver) => (
                    <li key={driver.driver_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                      <div>
                        <p className="font-semibold">{driver.name}</p>
                        <p className="text-xs text-neutral-600">
                          {driver.hub} - {driver.orders_left} parcel{driver.orders_left === 1 ? "" : "s"} left
                        </p>
                      </div>
                      {driver.stuck_until ? (
                        <Badge tone="warning">Stuck in traffic until {formatClock(driver.stuck_until)}</Badge>
                      ) : (
                        <Button
                          size="sm"
                          variant="secondary"
                          loading={jam.isPending && jam.variables === driver.driver_id}
                          onClick={() => jam.mutate(driver.driver_id)}
                        >
                          Start a traffic jam
                        </Button>
                      )}
                    </li>
                  ))}
                </ul>
              )}
              <p className="mt-3 text-xs text-neutral-500">
                A stuck driver keeps reporting the same position. After {status.data.idle_minutes} minutes the anomaly
                scan opens a "Driver not moving" incident on the hub dashboard.
              </p>
            </Card>

            <Card title="Demo data">
              <p className="text-sm text-neutral-700">
                {status.data.daily_reset
                  ? "The demo data reloads every day at 03:00 (Vietnam time)."
                  : "Automatic daily reload is off on this server."}
              </p>
              {canReset ? (
                <Button variant="danger" className="mt-3" onClick={() => setConfirmReset(true)}>
                  Reload demo data now
                </Button>
              ) : (
                <p className="mt-2 text-xs text-neutral-500">Sign in as the system admin to reload it by hand.</p>
              )}
            </Card>
          </>
        )}
      </main>

      <Dialog
        open={confirmReset}
        title="Reload all demo data?"
        onClose={() => setConfirmReset(false)}
        actions={
          <>
            <Button variant="secondary" onClick={() => setConfirmReset(false)}>
              Cancel
            </Button>
            <Button variant="danger" loading={reset.isPending} onClick={() => reset.mutate()}>
              Reload
            </Button>
          </>
        }
      >
        Every order, incident and account change made in the demo is replaced by a fresh data set. Everyone is signed
        out.
      </Dialog>
    </div>
  );
}
