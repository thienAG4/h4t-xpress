// ReportsPage - E-01 (Figma "Reports") with export E-02: one filter row (period, hubs),
// KPI tiles compared with the previous period, order volume, failure reasons,
// on-time delivery by area, top drivers and top hubs.

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Alert, Button, Card, Loading, Table, Td, TextField, Th } from "@/components/ui";
import { listHubs } from "@/features/auth/api";
import { cn } from "@/lib/cn";
import { errorMessage } from "@/lib/errors";
import { businessDate, formatDay } from "@/lib/format";
import { hasPermission, useSession } from "@/lib/session";
import { toast } from "@/lib/toast";
import type { Report, ReportKpi } from "@/types";
import { exportReport, fetchReport, type ReportFilters } from "../api";
import { BarList, ColumnChart } from "../components/charts";

const PRESETS = [
  { days: 7, label: "Last 7 days" },
  { days: 30, label: "Last 30 days" },
  { days: 90, label: "Last 90 days" },
];

type Kind = "count" | "rate" | "minutes";

function formatValue(value: number | null, kind: Kind): string {
  if (value === null) return "-";
  if (kind === "rate") return `${(value * 100).toFixed(1)}%`;
  if (kind === "minutes") {
    const hours = Math.floor(value / 60);
    return hours ? `${hours}h ${String(Math.round(value % 60)).padStart(2, "0")}m` : `${Math.round(value)}m`;
  }
  return new Intl.NumberFormat("en-US").format(value);
}

function delta(kpi: ReportKpi, kind: Kind, higherIsBetter: boolean): { text: string; good: boolean | null } {
  if (kpi.value === null || kpi.previous === null) return { text: "No data for the previous period", good: null };
  const diff = kpi.value - kpi.previous;
  if (Math.abs(diff) < 1e-9) return { text: "Same as the previous period", good: null };
  const text =
    kind === "rate"
      ? `${diff > 0 ? "+" : ""}${(diff * 100).toFixed(1)} pts`
      : kind === "minutes"
        ? `${diff > 0 ? "+" : ""}${Math.round(diff)} min`
        : kpi.previous
          ? `${diff > 0 ? "+" : ""}${Math.round((diff / kpi.previous) * 100)}%`
          : `${diff > 0 ? "+" : ""}${diff}`;
  const good = diff > 0 === higherIsBetter;
  return { text: `${text} vs previous, ${good ? "better" : "worse"}`, good };
}

function KpiTile({ label, kpi, kind, higherIsBetter, suffix }: { label: string; kpi: ReportKpi; kind: Kind; higherIsBetter: boolean; suffix?: string }) {
  const change = delta(kpi, kind, higherIsBetter);
  return (
    <section className="rounded-card border border-line bg-white px-5 py-4">
      <p className="text-sm text-neutral-600">{label}</p>
      <p className="mt-1 font-display text-2xl font-bold">
        {formatValue(kpi.value, kind)}
        {suffix && <span className="text-base font-medium text-neutral-500">{suffix}</span>}
      </p>
      <p
        className={cn(
          "mt-1 text-xs",
          change.good === null ? "text-neutral-500" : change.good ? "text-success-700" : "text-danger-700",
        )}
      >
        {change.text}
      </p>
    </section>
  );
}

function rankChange(rank: number, previous: number | null): string {
  if (previous === null) return "new";
  if (previous === rank) return "same";
  return previous > rank ? `up ${previous - rank}` : `down ${rank - previous}`;
}

function ReportBody({ report }: { report: Report }) {
  const s = report.summary;
  const percent = (value: number | null) => (value === null ? "-" : `${(value * 100).toFixed(1)}%`);
  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiTile label="Total orders" kpi={s.total_orders} kind="count" higherIsBetter />
        <KpiTile label="Success rate" kpi={s.success_rate} kind="rate" higherIsBetter />
        <KpiTile label="On-time rate" kpi={s.on_time_rate} kind="rate" higherIsBetter />
        <KpiTile label="Avg delivery time" kpi={s.avg_delivery_minutes} kind="minutes" higherIsBetter={false} />
        <KpiTile label="Failed attempt rate" kpi={s.failed_attempt_rate} kind="rate" higherIsBetter={false} />
        <KpiTile label="Incidents" kpi={s.incidents} kind="count" higherIsBetter={false} />
        <KpiTile label="Active drivers" kpi={s.active_drivers} kind="count" higherIsBetter suffix={` / ${s.total_drivers}`} />
        <KpiTile label="Delivered" kpi={s.delivered} kind="count" higherIsBetter />
      </div>

      <Card title={`Order volume per ${report.granularity}`}>
        <ColumnChart
          series={["Orders created", "Delivered"]}
          points={report.volume.map((point) => ({ label: point.label, values: [point.orders, point.delivered] }))}
        />
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer font-semibold text-primary-600">Show as a table</summary>
          <div className="mt-2 max-h-64 overflow-y-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-xs text-neutral-500">
                  <th className="py-1 font-medium">Period</th>
                  <th className="py-1 text-right font-medium">Orders created</th>
                  <th className="py-1 text-right font-medium">Delivered</th>
                </tr>
              </thead>
              <tbody>
                {report.volume.map((point) => (
                  <tr key={point.period} className="border-t border-line">
                    <td className="py-1">{point.label}</td>
                    <td className="py-1 text-right tabular-nums">{point.orders}</td>
                    <td className="py-1 text-right tabular-nums">{point.delivered}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Top failure reasons">
          <BarList
            empty="No failed attempt in this period."
            rows={report.failure_reasons.map((row) => ({
              key: row.key,
              label: row.label,
              value: row.count,
              display: `${row.count} (${percent(row.share)})`,
            }))}
          />
          {report.incident_types.length > 0 && (
            <>
              <h3 className="mt-6 mb-3 text-sm font-semibold">Incidents by type</h3>
              <BarList
                empty=""
                rows={report.incident_types.map((row) => ({
                  key: row.key,
                  label: row.label,
                  value: row.count,
                  display: `${row.count} (${percent(row.share)})`,
                }))}
              />
            </>
          )}
        </Card>
        <Card title="On-time delivery by area">
          <BarList
            empty="No delivered order in this period."
            max={1}
            rows={report.on_time_by_area.map((row) => ({
              key: row.area,
              label: row.area,
              value: row.on_time_rate ?? 0,
              display: percent(row.on_time_rate),
              detail: `${row.on_time} of ${row.delivered} delivered on time`,
            }))}
          />
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section>
          <h2 className="mb-3 text-base font-semibold">Top drivers</h2>
          <Table>
            <thead>
              <tr>
                <Th>#</Th>
                <Th>Driver</Th>
                <Th className="text-right">Delivered</Th>
                <Th className="text-right">Success</Th>
                <Th className="text-right">On time</Th>
              </tr>
            </thead>
            <tbody>
              {report.top_drivers.map((row) => (
                <tr key={row.driver_id}>
                  <Td>
                    <span className="font-semibold">{row.rank}</span>
                    <span className="block text-xs text-neutral-500">{rankChange(row.rank, row.previous_rank)}</span>
                  </Td>
                  <Td>
                    {row.name}
                    <span className="block text-xs text-neutral-500">{row.hub}</span>
                  </Td>
                  <Td className="text-right tabular-nums">{row.delivered}</Td>
                  <Td className="text-right tabular-nums">{percent(row.success_rate)}</Td>
                  <Td className="text-right tabular-nums">{percent(row.on_time_rate)}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </section>
        <section>
          <h2 className="mb-3 text-base font-semibold">Top hubs</h2>
          <Table>
            <thead>
              <tr>
                <Th>#</Th>
                <Th>Hub</Th>
                <Th className="text-right">Orders</Th>
                <Th className="text-right">Delivered</Th>
                <Th className="text-right">On time</Th>
              </tr>
            </thead>
            <tbody>
              {report.top_hubs.map((row) => (
                <tr key={row.hub_id}>
                  <Td>
                    <span className="font-semibold">{row.rank}</span>
                    <span className="block text-xs text-neutral-500">{rankChange(row.rank, row.previous_rank)}</span>
                  </Td>
                  <Td>{row.name}</Td>
                  <Td className="text-right tabular-nums">{row.orders}</Td>
                  <Td className="text-right tabular-nums">{row.delivered}</Td>
                  <Td className="text-right tabular-nums">{percent(row.on_time_rate)}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </section>
      </div>
    </div>
  );
}

export function ReportsPage() {
  const user = useSession((state) => state.user);
  const canExport = hasPermission(user, "report.export");
  const ownHubOnly = Boolean(user?.hub_id);
  const [filters, setFilters] = useState<ReportFilters>(() => ({
    date_from: businessDate(-29),
    date_to: businessDate(0),
    hub_ids: [],
  }));
  const [exporting, setExporting] = useState<"xlsx" | "pdf" | null>(null);
  const hubs = useQuery({ queryKey: ["hubs"], queryFn: listHubs, enabled: !ownHubOnly });
  const report = useQuery({
    queryKey: ["reports", filters],
    queryFn: () => fetchReport(filters),
    placeholderData: keepPreviousData,
  });

  const preset = PRESETS.find(
    (item) => filters.date_to === businessDate(0) && filters.date_from === businessDate(1 - item.days),
  );

  async function download(format: "xlsx" | "pdf") {
    setExporting(format);
    try {
      await exportReport(filters, format);
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setExporting(null);
    }
  }

  const toggleHub = (hubId: string) =>
    setFilters((current) => ({
      ...current,
      hub_ids: current.hub_ids.includes(hubId)
        ? current.hub_ids.filter((id) => id !== hubId)
        : [...current.hub_ids, hubId],
    }));

  return (
    <>
      <PageHeader
        title="Reports"
        description={
          report.data
            ? `${formatDay(report.data.summary.scope.date_from)} to ${formatDay(report.data.summary.scope.date_to)} - ${
                report.data.summary.scope.hub_ids.length ? report.data.summary.scope.hub_names.join(", ") : "all hubs"
              }`
            : undefined
        }
        actions={
          canExport && (
            <>
              <Button variant="secondary" loading={exporting === "xlsx"} onClick={() => void download("xlsx")}>
                Download Excel
              </Button>
              <Button variant="secondary" loading={exporting === "pdf"} onClick={() => void download("pdf")}>
                Download PDF
              </Button>
            </>
          )
        }
      />

      {/* One filter row above everything it scopes. */}
      <div className="mb-6 flex flex-wrap items-end gap-3 rounded-card border border-line bg-white p-4">
        <div className="flex gap-1" role="group" aria-label="Period">
          {PRESETS.map((item) => (
            <button
              key={item.days}
              type="button"
              onClick={() =>
                setFilters((current) => ({ ...current, date_from: businessDate(1 - item.days), date_to: businessDate(0) }))
              }
              className={cn(
                "h-10 rounded-input border px-3 text-sm",
                preset?.days === item.days ? "border-primary-600 bg-primary-50 font-semibold text-primary-700" : "border-line",
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className="w-40">
          <TextField
            compact
            type="date"
            label="From"
            value={filters.date_from}
            max={filters.date_to}
            onChange={(event) => event.target.value && setFilters((current) => ({ ...current, date_from: event.target.value }))}
          />
        </div>
        <div className="w-40">
          <TextField
            compact
            type="date"
            label="To"
            value={filters.date_to}
            min={filters.date_from}
            max={businessDate(0)}
            onChange={(event) => event.target.value && setFilters((current) => ({ ...current, date_to: event.target.value }))}
          />
        </div>
        {ownHubOnly ? (
          <p className="pb-2 text-sm text-neutral-600">Your hub only</p>
        ) : (
          <div className="flex flex-wrap gap-1" role="group" aria-label="Hubs">
            <button
              type="button"
              onClick={() => setFilters((current) => ({ ...current, hub_ids: [] }))}
              className={cn(
                "h-10 rounded-input border px-3 text-sm",
                filters.hub_ids.length === 0 ? "border-primary-600 bg-primary-50 font-semibold text-primary-700" : "border-line",
              )}
            >
              All hubs
            </button>
            {(hubs.data ?? []).map((hub) => (
              <button
                key={hub.id}
                type="button"
                aria-pressed={filters.hub_ids.includes(hub.id)}
                onClick={() => toggleHub(hub.id)}
                className={cn(
                  "h-10 rounded-input border px-3 text-sm",
                  filters.hub_ids.includes(hub.id) ? "border-primary-600 bg-primary-50 font-semibold text-primary-700" : "border-line",
                )}
              >
                {hub.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {report.isPending && <Loading />}
      {report.isError && <Alert tone="danger">{errorMessage(report.error)}</Alert>}
      {/* Refetching keeps the previous render, dimmed, instead of a layout jump. */}
      {report.data && (
        <div className={cn("transition-opacity", report.isFetching && "opacity-60")}>
          <ReportBody report={report.data} />
        </div>
      )}
    </>
  );
}
