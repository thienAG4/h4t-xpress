// RingChart - donut of a few parts with the total in the middle (Figma "Loading Vehicles",
// "Target Stats"); a thin white gap separates the parts

import { cn } from "@/lib/cn";

export type RingPart = { label: string; count: number; color: string };

function conicGradient(parts: RingPart[], total: number): string {
  const filled = parts.filter((part) => part.count > 0);
  const gap = filled.length > 1 ? 1 : 0;
  const arcs: string[] = [];
  filled.reduce((start, part) => {
    const end = start + (part.count / Math.max(total, 1)) * 360;
    arcs.push(`#ffffff ${start}deg ${start + gap}deg`, `${part.color} ${start + gap}deg ${end - gap}deg`, `#ffffff ${end - gap}deg ${end}deg`);
    return end;
  }, 0);
  return arcs.length ? `conic-gradient(${arcs.join(", ")})` : "conic-gradient(#e6e7ee 0deg 360deg)";
}

export function RingChart({
  parts,
  centerValue,
  centerLabel,
  className,
}: {
  parts: RingPart[];
  centerValue: number;
  centerLabel: string;
  className?: string;
}) {
  const total = parts.reduce((sum, part) => sum + part.count, 0);
  return (
    <div
      className={cn("relative size-40 shrink-0 rounded-full", className)}
      style={{ background: conicGradient(parts, total) }}
      role="img"
      aria-label={`${centerLabel}: ${parts.map((part) => `${part.label} ${part.count}`).join(", ")}`}
    >
      <div className="absolute inset-[18%] flex flex-col items-center justify-center rounded-full bg-white">
        <span className="text-3xl font-semibold text-ink tabular-nums">{centerValue}</span>
        <span className="text-xs text-neutral-600">{centerLabel}</span>
      </div>
    </div>
  );
}
