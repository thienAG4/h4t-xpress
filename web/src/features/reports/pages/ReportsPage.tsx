// ReportsPage - E-01 laid out like the Figma "Reports" (Nhà quản trị) with export E-02:
// pill filters (timeframe, hubs), KPI tiles with trend lines next to the order volume chart,
// top failure reasons, on-time delivery by area, top drivers and top hubs.

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  Ban,
  CarFront,
  ChevronDown,
  CircleQuestionMark,
  CloudRain,
  Download,
  HeartPulse,
  Hourglass,
  MapPin,
  MapPinOff,
  PackageX,
  PhoneOff,
  Timer,
  TrafficCone,
  UserX,
  Wrench,
  X,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Alert, Avatar, IconTile, Loading, Popover } from "@/components/ui";
import { listHubs } from "@/features/auth/api";
import { cn } from "@/lib/cn";
import { errorMessage } from "@/lib/errors";
import { businessDate, formatDay } from "@/lib/format";
import { hasPermission, useSession } from "@/lib/session";
import { toast } from "@/lib/toast";
import type { Granularity, Report, ReportKpi } from "@/types";
import { exportReport, fetchReport, type ReportFilters } from "../api";
import { ColumnChart, Sparkline } from "../components/charts";

const PRESETS = [
  { days: 7, label: "Last 7 days" },
  { days: 30, label: "Last 30 days" },
  { days: 90, label: "Last 90 days" },
  { days: 365, label: "Last 12 months" },
];

const GRANULARITIES: { value: Granularity; label: string }[] = [
  { value: "day", label: "Day" },
  { value: "week", label: "Week" },
  { value: "month", label: "Month" },
];

// Icons stand in for the photos of the Figma reason rows.
const REASON_ICON: Record<string, typeof Ban> = {
  CUSTOMER_ABSENT: UserX,
  CUSTOMER_UNREACHABLE: PhoneOff,
  CUSTOMER_REFUSED: Ban,
  WRONG_ADDRESS: MapPinOff,
  TRAFFIC_JAM: TrafficCone,
  WEATHER: CloudRain,
  TRAFFIC_ACCIDENT: CarFront,
  VEHICLE_BREAKDOWN: Wrench,
  HEALTH: HeartPulse,
  GOODS_DAMAGED: PackageX,
  ETA_ANOMALY: Timer,
  DRIVER_IDLE: Hourglass,
};

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

const CARD = "rounded-2xl border border-line/70 bg-white shadow-[0_4px_24px_rgba(15,23,42,0.05)]";

function KpiTile({
  label,
  kpi,
  kind,
  higherIsBetter,
  suffix,
  trend,
}: {
  label: string;
  kpi: ReportKpi;
  kind: Kind;
  higherIsBetter: boolean;
  suffix?: string;
  trend?: number[];
}) {
  const change = delta(kpi, kind, higherIsBetter);
  return (
    <section className={cn(CARD, "flex flex-col p-4")}>
      <p className="text-[13px] text-neutral-600">{label}</p>
      <p className="mt-2 text-2xl font-bold text-ink tabular-nums">
        {formatValue(kpi.value, kind)}
        {suffix && <span className="text-base font-medium text-neutral-400">{suffix}</span>}
      </p>
      <p
        className={cn(
          "mt-1 text-xs",
          change.good === null ? "text-neutral-500" : change.good ? "text-success-700" : "text-danger-700",
        )}
      >
        {change.text}
      </p>
      {trend && <Sparkline values={trend} className="mt-auto pt-2" />}
    </section>
  );
}

/** Figma reason and area rows: picture tile, label, gradient bar on a pale track, share. */
function GradientBars({
  rows,
  empty,
  tone,
}: {
  rows: { key: string; label: string; value: number; display: ReactNode; icon: typeof Ban; title?: string }[];
  empty: string;
  tone: "warm" | "green";
}) {
  if (!rows.length) return <p className="text-sm text-neutral-600">{empty}</p>;
  const fill = tone === "warm" ? "from-[#ffb07a] to-[#f2414b]" : "from-[#7ce69a] to-[#22c55e]";
  const track = tone === "warm" ? "bg-[#fde7e7]" : "bg-[#dcf9e6]";
  return (
    <ul className="flex flex-col gap-5">
      {rows.map((row) => (
        <li key={row.key} className="flex items-center gap-4" title={row.title}>
          <IconTile icon={row.icon} tone={tone === "warm" ? "warning" : "success"} />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-ink">{row.label}</p>
            <div className={cn("mt-1.5 h-2 rounded-full", track)}>
              <div className={cn("h-2 rounded-full bg-gradient-to-r", fill)} style={{ width: `${Math.max(3, row.value * 100)}%` }} />
            </div>
          </div>
          <span className="w-24 shrink-0 text-right text-xs text-neutral-500 sm:w-28 sm:text-sm">{row.display}</span>
        </li>
      ))}
    </ul>
  );
}

/** Rank number with a green up or red down triangle (Figma top lists). */
function Rank({ rank, previous }: { rank: number; previous: number | null }) {
  const up = previous === null || previous > rank;
  const same = previous === rank;
  const label = previous === null ? "new in the ranking" : same ? "same rank" : up ? `up from ${previous}` : `down from ${previous}`;
  return (
    <span className="flex shrink-0 items-center gap-2" title={label}>
      <span className="text-base font-medium text-ink tabular-nums">{rank}</span>
      {!same && (
        <svg viewBox="0 0 10 8" className={cn("h-2.5 w-3", up ? "fill-success-500" : "fill-danger-500 rotate-180")} role="img" aria-label={label}>
          <path d="M5 0 10 8H0z" />
        </svg>
      )}
      {same && <span className="h-0.5 w-3 rounded bg-neutral-300" role="img" aria-label={label} />}
    </span>
  );
}

function ReportBody({ report, granularity, onGranularity }: { report: Report; granularity: Granularity; onGranularity: (value: Granularity) => void }) {
  const s = report.summary;
  const percent = (value: number | null) => (value === null ? "-" : `${Math.round(value * 100)}%`);
  const [reasons, setReasons] = useState<"failures" | "incidents">("failures");
  const ratio = (part: number, whole: number) => (whole ? part / whole : 0);
  const trend = {
    orders: report.volume.map((point) => point.orders),
    success: report.volume.map((point) => ratio(point.delivered, point.delivered + point.returned)),
    onTime: report.volume.map((point) => ratio(point.on_time, point.delivered)),
  };
  const shareRows = (reasons === "failures" ? report.failure_reasons : report.incident_types).slice(0, 5).map((row) => ({
    key: row.key,
    label: row.label,
    value: row.share,
    display: `${percent(row.share)} of ${reasons === "failures" ? "failures" : "incidents"}`,
    icon: REASON_ICON[row.key] ?? CircleQuestionMark,
    title: `${row.count} in this period`,
  }));

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-4 sm:grid-cols-3 xl:grid-cols-[repeat(3,minmax(0,1fr))_minmax(0,2.1fr)] [&>*]:min-w-0">
        <KpiTile label="Active drivers" kpi={s.active_drivers} kind="count" higherIsBetter suffix={`/${s.total_drivers}`} />
        <KpiTile label="Total orders" kpi={s.total_orders} kind="count" higherIsBetter trend={trend.orders} />
        <KpiTile label="Avg delivery time" kpi={s.avg_delivery_minutes} kind="minutes" higherIsBetter={false} />

        <section className={cn(CARD, "p-4 sm:col-span-3 xl:col-span-1 xl:col-start-4 xl:row-span-2 xl:row-start-1")}>
          <header className="mb-3 flex items-center justify-between gap-3 border-b border-line pb-3">
            <h2 className="font-sans text-sm font-medium text-ink">Order volume</h2>
            <label className="flex items-center gap-1 text-xs font-medium text-primary-700">
              <span className="sr-only">Group by</span>
              <select
                className="cursor-pointer appearance-none bg-transparent pr-1 focus:outline-none"
                value={granularity}
                onChange={(event) => onGranularity(event.target.value as Granularity)}
              >
                {GRANULARITIES.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
              <ChevronDown className="size-3.5" aria-hidden />
            </label>
          </header>
          <ColumnChart
            track
            height={230}
            series={["Orders created", "Delivered"]}
            points={report.volume.map((point) => ({ label: point.label, values: [point.orders, point.delivered] }))}
          />
          <details className="mt-2 text-sm">
            <summary className="cursor-pointer text-xs font-semibold text-primary-600">Show as a table</summary>
            <div className="mt-2 max-h-56 overflow-y-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="text-xs text-neutral-500">
                    <th className="py-1 font-medium">Period</th>
                    <th className="py-1 text-right font-medium">Orders created</th>
                    <th className="py-1 text-right font-medium">Delivered</th>
                    <th className="py-1 text-right font-medium">On time</th>
                  </tr>
                </thead>
                <tbody>
                  {report.volume.map((point) => (
                    <tr key={point.period} className="border-t border-line">
                      <td className="py-1">{point.label}</td>
                      <td className="py-1 text-right tabular-nums">{point.orders}</td>
                      <td className="py-1 text-right tabular-nums">{point.delivered}</td>
                      <td className="py-1 text-right tabular-nums">{point.on_time}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </section>

        <KpiTile label="Success rate" kpi={s.success_rate} kind="rate" higherIsBetter trend={trend.success} />
        <KpiTile label="Failed attempt rate" kpi={s.failed_attempt_rate} kind="rate" higherIsBetter={false} />
        <KpiTile label="On-time rate" kpi={s.on_time_rate} kind="rate" higherIsBetter trend={trend.onTime} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2 [&>*]:min-w-0">
        <section className={cn(CARD, "p-5")}>
          <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-sans text-sm font-medium text-neutral-600">Top failed reasons</h2>
            <div className="flex rounded-lg bg-neutral-100 p-0.5 text-xs" role="group" aria-label="Reasons of">
              {(["failures", "incidents"] as const).map((value) => (
                <button
                  key={value}
                  type="button"
                  aria-pressed={reasons === value}
                  onClick={() => setReasons(value)}
                  className={cn("rounded-md px-3 py-1", reasons === value ? "bg-white font-semibold text-ink shadow-sm" : "text-neutral-600")}
                >
                  {value === "failures" ? "Failed deliveries" : `Incidents (${s.incidents.value ?? 0})`}
                </button>
              ))}
            </div>
          </header>
          <GradientBars
            tone="warm"
            empty={reasons === "failures" ? "No failed attempt in this period." : "No incident in this period."}
            rows={shareRows}
          />
        </section>
        <section className={cn(CARD, "p-5")}>
          <h2 className="mb-5 font-sans text-sm font-medium text-neutral-600">On-time delivery by area</h2>
          <GradientBars
            tone="green"
            empty="No delivered order in this period."
            rows={report.on_time_by_area.slice(0, 5).map((row) => ({
              key: row.area,
              label: row.area,
              value: row.on_time_rate ?? 0,
              display: `${percent(row.on_time_rate)} on time`,
              icon: MapPin,
              title: `${row.on_time} of ${row.delivered} delivered on time`,
            }))}
          />
        </section>
      </div>

      <div className="grid gap-6 lg:grid-cols-2 [&>*]:min-w-0">
        <section className={cn(CARD, "p-5")}>
          <h2 className="mb-4 font-sans text-sm font-medium text-neutral-600">Top drivers</h2>
          <ul className="flex flex-col gap-4">
            {report.top_drivers.map((row) => (
              <li key={row.driver_id} className="flex items-center gap-3">
                <Avatar name={row.name} size="lg" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-ink">{row.name}</p>
                  <p className="truncate text-xs text-neutral-500">
                    {row.delivered} orders - {percent(row.success_rate)} successful - {percent(row.on_time_rate)} on time
                  </p>
                </div>
                <Rank rank={row.rank} previous={row.previous_rank} />
              </li>
            ))}
          </ul>
        </section>
        <section className={cn(CARD, "p-5")}>
          <h2 className="mb-4 font-sans text-sm font-medium text-neutral-600">Top hubs</h2>
          <ul className="flex flex-col gap-4">
            {report.top_hubs.map((row) => (
              <li key={row.hub_id} className="flex min-h-11 items-center gap-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-ink">{row.name}</p>
                  <p className="truncate text-xs text-neutral-500">
                    {row.orders} orders - {row.delivered} delivered - {percent(row.on_time_rate)} on time
                  </p>
                </div>
                <Rank rank={row.rank} previous={row.previous_rank} />
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}

const PILL =
  "flex h-11 items-center gap-2 rounded-full border border-line/70 bg-white px-5 text-sm text-ink shadow-[0_2px_10px_rgba(15,23,42,0.05)] hover:border-primary-200";

export function ReportsPage() {
  const user = useSession((state) => state.user);
  const canExport = hasPermission(user, "report.export");
  const ownHubOnly = Boolean(user?.hub_id);
  const [filters, setFilters] = useState<ReportFilters>(() => ({
    date_from: businessDate(-29),
    date_to: businessDate(0),
    hub_ids: [],
  }));
  const [granularity, setGranularity] = useState<Granularity>("day");
  const [exporting, setExporting] = useState<"xlsx" | "pdf" | null>(null);
  const hubs = useQuery({ queryKey: ["hubs"], queryFn: listHubs, enabled: !ownHubOnly });
  const scoped = { ...filters, granularity };
  const report = useQuery({
    queryKey: ["reports", scoped],
    queryFn: () => fetchReport(scoped),
    placeholderData: keepPreviousData,
  });

  const preset = PRESETS.find(
    (item) => filters.date_to === businessDate(0) && filters.date_from === businessDate(1 - item.days),
  );
  const timeframe = preset ? preset.label : `${formatDay(filters.date_from)} - ${formatDay(filters.date_to)}`;
  const chosen = (hubs.data ?? []).filter((hub) => filters.hub_ids.includes(hub.id));
  const hubLabel = ownHubOnly
    ? (user?.hub_name ?? "My hub")
    : chosen.length === 0
      ? "All"
      : chosen.length === 1
        ? chosen[0].name
        : "Multiple selected";

  async function download(format: "xlsx" | "pdf") {
    setExporting(format);
    try {
      await exportReport(scoped, format);
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
        divider
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
              {(["xlsx", "pdf"] as const).map((format) => (
                <button
                  key={format}
                  type="button"
                  disabled={exporting !== null}
                  onClick={() => void download(format)}
                  className="flex h-9 items-center gap-1.5 rounded-lg px-3 text-sm font-medium text-ink hover:bg-white disabled:opacity-50"
                >
                  <Download className="size-4" aria-hidden />
                  {exporting === format ? "Preparing..." : format === "xlsx" ? "Download Excel" : "Download PDF"}
                </button>
              ))}
            </>
          )
        }
      />

      {/* One filter row above everything it scopes (Figma pill dropdowns). */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <Popover
          label={`Timeframe: ${timeframe}`}
          align="start"
          buttonClassName={PILL}
          button={
            <>
              Timeframe: <span className="font-semibold">{timeframe}</span>
              <ChevronDown className="ml-6 size-4 text-neutral-500" aria-hidden />
            </>
          }
          panelClassName="w-72 p-2"
        >
          {(close) => (
            <div className="flex flex-col gap-1">
              {PRESETS.map((item) => (
                <button
                  key={item.days}
                  type="button"
                  onClick={() => {
                    setFilters((current) => ({ ...current, date_from: businessDate(1 - item.days), date_to: businessDate(0) }));
                    close();
                  }}
                  className={cn(
                    "rounded-md px-3 py-2 text-left text-sm",
                    preset?.days === item.days ? "bg-primary-50 font-semibold text-primary-700" : "hover:bg-neutral-50",
                  )}
                >
                  {item.label}
                </button>
              ))}
              <div className="mt-1 grid grid-cols-2 gap-2 border-t border-line px-1 pt-3 pb-1 text-xs">
                <label className="flex flex-col gap-1">
                  From
                  <input
                    type="date"
                    className="h-9 rounded-md border border-line px-2 text-sm"
                    value={filters.date_from}
                    max={filters.date_to}
                    onChange={(event) => event.target.value && setFilters((current) => ({ ...current, date_from: event.target.value }))}
                  />
                </label>
                <label className="flex flex-col gap-1">
                  To
                  <input
                    type="date"
                    className="h-9 rounded-md border border-line px-2 text-sm"
                    value={filters.date_to}
                    min={filters.date_from}
                    max={businessDate(0)}
                    onChange={(event) => event.target.value && setFilters((current) => ({ ...current, date_to: event.target.value }))}
                  />
                </label>
              </div>
            </div>
          )}
        </Popover>

        {ownHubOnly ? (
          <span className={cn(PILL, "cursor-default hover:border-line/70")}>
            Hub: <span className="font-semibold">{hubLabel}</span>
          </span>
        ) : (
          <Popover
            label={`Hubs: ${hubLabel}`}
            align="start"
            buttonClassName={PILL}
            button={
              <>
                {chosen.length > 1 ? "Hubs" : "Hub"}: <span className="font-semibold">{hubLabel}</span>
                <ChevronDown className="ml-6 size-4 text-neutral-500" aria-hidden />
              </>
            }
            panelClassName="w-80 p-3"
          >
            {() => (
              <div className="flex flex-col gap-3 text-sm">
                <div className="flex flex-wrap items-center gap-1.5">
                  {chosen.map((hub) => (
                    <button
                      key={hub.id}
                      type="button"
                      onClick={() => toggleHub(hub.id)}
                      className="flex items-center gap-1 rounded-md bg-primary-50 px-2 py-1 text-xs text-primary-700"
                    >
                      {hub.name}
                      <X className="size-3" aria-label={`Remove ${hub.name}`} />
                    </button>
                  ))}
                  {chosen.length > 0 && (
                    <button type="button" className="ml-auto text-xs text-neutral-500 hover:text-ink" onClick={() => setFilters((current) => ({ ...current, hub_ids: [] }))}>
                      Clear
                    </button>
                  )}
                </div>
                <label className="flex items-center gap-2.5">
                  <input
                    type="radio"
                    className="size-4 accent-primary-600"
                    checked={filters.hub_ids.length === 0}
                    onChange={() => setFilters((current) => ({ ...current, hub_ids: [] }))}
                  />
                  All hubs
                </label>
                <p className="text-xs text-neutral-500">Hubs</p>
                {(hubs.data ?? []).map((hub) => (
                  <label key={hub.id} className="flex items-center gap-2.5">
                    <input
                      type="checkbox"
                      className="size-4 accent-primary-600"
                      checked={filters.hub_ids.includes(hub.id)}
                      onChange={() => toggleHub(hub.id)}
                    />
                    {hub.name}
                  </label>
                ))}
              </div>
            )}
          </Popover>
        )}
      </div>

      {report.isPending && <Loading />}
      {report.isError && <Alert tone="danger">{errorMessage(report.error)}</Alert>}
      {/* Refetching keeps the previous render, dimmed, instead of a layout jump. */}
      {report.data && (
        <div className={cn("transition-opacity", report.isFetching && "opacity-60")}>
          <ReportBody report={report.data} granularity={granularity} onGranularity={setGranularity} />
        </div>
      )}
    </>
  );
}
