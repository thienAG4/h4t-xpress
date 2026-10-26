// Report charts - hand-drawn SVG columns and horizontal bars (no chart library).
// Marks follow the dataviz rules: bars <= 24px with a 4px rounded data-end, 2px gaps,
// hairline grid, a legend for 2+ series, a tooltip per column group, and a table view.

import { useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";

// Validated pair (scripts/validate_palette.js, light surface): brand blue + orange.
const SERIES_COLORS = ["#1070f8", "#eb6834"];

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(640);
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(280, entry.contentRect.width)));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
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
}: {
  points: ColumnPoint[];
  series: string[];
  height?: number;
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
