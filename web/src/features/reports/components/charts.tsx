// Report charts - hand-drawn SVG columns, area line, sparkline and horizontal bars (no chart library).
// Marks follow the dataviz rules: bars <= 24px with a 4px rounded data-end, 2px gaps, 2px lines,
// hairline grid, a legend for 2+ series, a tooltip per column group or a crosshair, and a table view.

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";

// Validated pair (scripts/validate_palette.js, light surface): brand blue + orange.
const SERIES_COLORS = ["#1070f8", "#eb6834"];

function useWidth<T extends HTMLElement>(min = 280) {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(min);
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(min, entry.contentRect.width)));
    observer.observe(element);
    return () => observer.disconnect();
  }, [min]);
  return { ref, width };
}

function niceMax(value: number): number {
  if (value <= 4) return 4;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((candidate) => candidate * 4 >= value) ?? value;
  return step * 4;
}

function compact(value: number): string {
  return value >= 1000 ? `${Math.round(value / 100) / 10}K` : String(value);
}

/** Bar with a 4px rounded data-end and a square base, growing up from the baseline. */
function columnPath(x: number, y: number, width: number, height: number): string {
  const r = Math.min(4, width / 2, height);
  return `M${x},${y + height} V${y + r} Q${x},${y} ${x + r},${y} H${x + width - r} Q${x + width},${y} ${x + width},${y + r} V${y + height} Z`;
}

export type ColumnPoint = { label: string; values: number[] };

export function ColumnChart({
  points,
  series,
  height = 240,
  track = false,
}: {
  points: ColumnPoint[];
  series: string[];
  height?: number;
  /** Pale full-height track behind each bar (Figma "Order Volume"). */
  track?: boolean;
}) {
  const { ref, width } = useWidth<HTMLDivElement>();
  const [active, setActive] = useState<number | null>(null);
  const left = 36;
  const bottom = 24;
  const plotWidth = width - left - 8;
  const plotHeight = height - bottom - 8;
  const max = niceMax(Math.max(1, ...points.flatMap((point) => point.values)));
  const band = plotWidth / Math.max(points.length, 1);
  const barWidth = Math.min(24, Math.max(2, (band * 0.7 - 2 * (series.length - 1)) / series.length));
  const groupWidth = barWidth * series.length + 2 * (series.length - 1);
  const labelEvery = Math.max(1, Math.ceil(points.length / Math.max(1, Math.floor(plotWidth / 56))));
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((share) => Math.round(max * share));
  const y = (value: number) => 8 + plotHeight - (value / max) * plotHeight;

  return (
    <div ref={ref} className="relative">
      <Legend series={series} />
      <svg width={width} height={height} role="img" aria-label={`${series.join(" and ")} per period`} className="mt-2 block">
        {ticks.map((tick) => (
          <g key={tick}>
            <line x1={left} x2={width - 8} y1={y(tick)} y2={y(tick)} stroke="#e6e7ee" strokeWidth={1} />
            <text x={left - 6} y={y(tick) + 4} textAnchor="end" className="fill-neutral-500 text-[10px] tabular-nums">
              {compact(tick)}
            </text>
          </g>
        ))}
        {points.map((point, index) => {
          const x0 = left + index * band + (band - groupWidth) / 2;
          return (
            <g key={point.label}>
              {track &&
                point.values.map((_, s) => (
                  <path key={`track-${series[s]}`} d={columnPath(x0 + s * (barWidth + 2), 8, barWidth, plotHeight)} fill="#eef4ff" />
                ))}
              {point.values.map((value, s) => {
                const top = y(value);
                const barHeight = 8 + plotHeight - top;
                return value > 0 ? (
                  <path
                    key={series[s]}
                    d={columnPath(x0 + s * (barWidth + 2), top, barWidth, barHeight)}
                    fill={SERIES_COLORS[s]}
                    opacity={active === null || active === index ? 1 : 0.45}
                  />
                ) : null;
              })}
              {index % labelEvery === 0 && (
                <text x={left + index * band + band / 2} y={height - 6} textAnchor="middle" className="fill-neutral-500 text-[10px]">
                  {point.label}
                </text>
              )}
              {/* The whole band is the hit target, not only the painted bars. */}
              <rect
                x={left + index * band}
                y={8}
                width={band}
                height={plotHeight}
                fill="transparent"
                tabIndex={0}
                aria-label={`${point.label}: ${point.values.map((value, s) => `${series[s]} ${value}`).join(", ")}`}
                onPointerEnter={() => setActive(index)}
                onPointerLeave={() => setActive(null)}
                onFocus={() => setActive(index)}
                onBlur={() => setActive(null)}
                className="outline-none"
              />
            </g>
          );
        })}
      </svg>
      {active !== null && points[active] && (
        <div
          className="pointer-events-none absolute top-8 z-10 rounded-input border border-line bg-white px-3 py-2 text-xs shadow-md"
          style={{ left: Math.min(width - 150, Math.max(0, left + active * band + band / 2 - 70)) }}
        >
          <p className="mb-1 text-neutral-600">{points[active].label}</p>
          {points[active].values.map((value, s) => (
            <p key={series[s]} className="flex items-center gap-2">
              <span className="h-0.5 w-3" style={{ backgroundColor: SERIES_COLORS[s] }} />
              <span className="font-semibold tabular-nums">{value}</span>
              <span className="text-neutral-600">{series[s]}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

export function Legend({ series }: { series: string[] }) {
  if (series.length < 2) return null;
  return (
    <ul className="flex flex-wrap gap-4 text-xs text-neutral-600">
      {series.map((name, index) => (
        <li key={name} className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-sm" style={{ backgroundColor: SERIES_COLORS[index] }} />
          {name}
        </li>
      ))}
    </ul>
  );
}

export type BarRow = { key: string; label: string; value: number; display: string; detail?: string };

/** Horizontal bars for one measure; the value sits at the tip, in text ink. */
export function BarList({ rows, max, empty }: { rows: BarRow[]; max?: number; empty: ReactNode }) {
  if (!rows.length) return <p className="text-sm text-neutral-600">{empty}</p>;
  const top = max ?? Math.max(...rows.map((row) => row.value), 1);
  return (
    <ul className="flex flex-col gap-3">
      {rows.map((row) => (
        <li key={row.key} title={row.detail}>
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <span className="truncate text-ink">{row.label}</span>
            <span className="shrink-0 font-semibold tabular-nums">{row.display}</span>
          </div>
          <div className="mt-1 h-2 rounded-full bg-primary-50">
            <div
              className={cn("h-2 rounded-full bg-primary-600")}
              style={{ width: `${Math.max(2, (row.value / top) * 100)}%` }}
            />
          </div>
          {row.detail && <p className="mt-0.5 text-xs text-neutral-500">{row.detail}</p>}
        </li>
      ))}
    </ul>
  );
}

export type LinePoint = { label: string; value: number };

/** Single-series area chart with a crosshair tooltip (Figma hub "Recent Orders"). */
export function AreaChart({ points, label, height = 190 }: { points: LinePoint[]; label: string; height?: number }) {
  const { ref, width } = useWidth<HTMLDivElement>(160);
  const gradient = useId();
  const [active, setActive] = useState<number | null>(null);
  const left = 30;
  const top = 10;
  const bottom = 22;
  const plotWidth = width - left - 10;
  const plotHeight = height - top - bottom;
  const max = niceMax(Math.max(1, ...points.map((point) => point.value)));
  const step = points.length > 1 ? plotWidth / (points.length - 1) : 0;
  const x = (index: number) => left + (points.length > 1 ? index * step : plotWidth / 2);
  const y = (value: number) => top + plotHeight - (value / max) * plotHeight;
  const line = points.map((point, index) => `${index ? "L" : "M"}${x(index)},${y(point.value)}`).join(" ");
  const area = points.length ? `${line} L${x(points.length - 1)},${top + plotHeight} L${x(0)},${top + plotHeight} Z` : "";
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((share) => Math.round(max * share));
  const labelEvery = Math.max(1, Math.ceil(points.length / Math.max(1, Math.floor(plotWidth / 44))));

  const pick = (clientX: number, box: DOMRect) => {
    if (!points.length) return;
    const index = Math.round((clientX - box.left - left) / Math.max(step, 1));
    setActive(Math.min(points.length - 1, Math.max(0, index)));
  };

  return (
    <div ref={ref} className="relative">
      <svg
        width={width}
        height={height}
        role="img"
        aria-label={`${label}: ${points.map((point) => `${point.label} ${point.value}`).join(", ")}`}
        className="block"
        onPointerMove={(event) => pick(event.clientX, event.currentTarget.getBoundingClientRect())}
        onPointerLeave={() => setActive(null)}
      >
        <defs>
          <linearGradient id={gradient} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#1070f8" stopOpacity={0.28} />
            <stop offset="100%" stopColor="#1070f8" stopOpacity={0.03} />
          </linearGradient>
        </defs>
        {ticks.map((tick) => (
          <g key={tick}>
            <line x1={left} x2={width - 10} y1={y(tick)} y2={y(tick)} stroke="#e6e7ee" strokeWidth={1} />
            <text x={left - 6} y={y(tick) + 3} textAnchor="end" className="fill-neutral-500 text-[10px] tabular-nums">
              {compact(tick)}
            </text>
          </g>
        ))}
        <path d={area} fill={`url(#${gradient})`} />
        <path d={line} fill="none" stroke="#1070f8" strokeWidth={2} strokeLinejoin="round" />
        {points.map((point, index) =>
          index % labelEvery === 0 ? (
            <text key={point.label} x={x(index)} y={height - 5} textAnchor="middle" className="fill-neutral-500 text-[10px]">
              {point.label}
            </text>
          ) : null,
        )}
        {active !== null && points[active] && (
          <g>
            <line x1={x(active)} x2={x(active)} y1={top} y2={top + plotHeight} stroke="#98a1b3" strokeDasharray="3 3" />
            <circle cx={x(active)} cy={y(points[active].value)} r={4.5} fill="#1070f8" stroke="#fff" strokeWidth={2} />
          </g>
        )}
      </svg>
      {active !== null && points[active] && (
        <div
          className="pointer-events-none absolute top-0 z-10 rounded-md border border-line bg-white px-2.5 py-1.5 text-xs shadow-md"
          style={{ left: Math.min(width - 120, Math.max(0, x(active) - 50)) }}
        >
          <p className="text-neutral-600">{points[active].label}</p>
          <p className="font-semibold tabular-nums">
            {points[active].value} {label.toLowerCase()}
          </p>
        </div>
      )}
    </div>
  );
}

/** Tiny trend line under a KPI value; decorative because the value is printed beside it. */
export function Sparkline({ values, className }: { values: number[]; className?: string }) {
  const gradient = useId();
  if (values.length < 2) return null;
  const width = 120;
  const height = 32;
  const min = Math.min(...values);
  const span = Math.max(...values) - min || 1;
  const x = (index: number) => (index / (values.length - 1)) * width;
  const y = (value: number) => height - 3 - ((value - min) / span) * (height - 6);
  const line = values.map((value, index) => `${index ? "L" : "M"}${x(index)},${y(value)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className={cn("h-8 w-full", className)} aria-hidden>
      <defs>
        <linearGradient id={gradient} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#1070f8" stopOpacity={0.22} />
          <stop offset="100%" stopColor="#1070f8" stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={`${line} L${width},${height} L0,${height} Z`} fill={`url(#${gradient})`} />
      <path d={line} fill="none" stroke="#1070f8" strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
