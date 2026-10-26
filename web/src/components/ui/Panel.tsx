// Panel, IconTile and Avatar - the white cards, icon squares and initials of the Figma dashboards

import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { cn } from "@/lib/cn";

/** Figma hub card: white, thin border, title row with an optional "View all" link. */
export function Panel({
  title,
  action,
  children,
  className,
  bodyClassName,
}: {
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={cn("flex min-w-0 flex-col rounded-lg border border-line bg-white", className)}>
      {(title || action) && (
        <header className="flex min-h-14 flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-3">
          {title && <h2 className="font-sans text-[17px] font-medium text-ink">{title}</h2>}
          {action}
        </header>
      )}
      <div className={cn("min-w-0 flex-1 p-5", bodyClassName)}>{children}</div>
    </section>
  );
}

/** Figma "Overview" counter: grey label, large value, one line of context underneath. */
export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  tone = "neutral",
  className,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  icon?: LucideIcon;
  tone?: "neutral" | "success" | "warning" | "danger" | "primary";
  className?: string;
}) {
  const hintColor = {
    neutral: "text-neutral-600",
    success: "text-success-700",
    warning: "text-warning-700",
    danger: "text-danger-700",
    primary: "text-primary-700",
  }[tone];
  return (
    <section className={cn("rounded-xl border border-line bg-white px-6 py-5", className)}>
      <p className="text-base text-neutral-600">{label}</p>
      <p className="mt-2 text-4xl font-medium text-ink tabular-nums">{value}</p>
      {hint && (
        <p className={cn("mt-2 flex items-center gap-1.5 text-sm", hintColor)}>
          {Icon && <Icon className="size-4" aria-hidden />}
          {hint}
        </p>
      )}
    </section>
  );
}

export function PanelLink({ to, children = "View all" }: { to: string; children?: ReactNode }) {
  return (
    <Link to={to} className="text-sm font-medium text-primary-600 hover:underline">
      {children}
    </Link>
  );
}

type TileTone = "primary" | "success" | "warning" | "danger" | "neutral";

const TILE_TONES: Record<TileTone, string> = {
  primary: "bg-primary-50 text-primary-600",
  success: "bg-success-50 text-success-700",
  warning: "bg-warning-50 text-warning-700",
  danger: "bg-danger-50 text-danger-700",
  neutral: "bg-neutral-100 text-neutral-600",
};

/** Rounded square holding one icon (Figma KPI and list rows). */
export function IconTile({
  icon: Icon,
  tone = "primary",
  size = "md",
  className,
}: {
  icon: LucideIcon;
  tone?: TileTone;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const box = { sm: "size-8 rounded-md", md: "size-10 rounded-lg", lg: "size-14 rounded-full" }[size];
  const glyph = { sm: "size-4", md: "size-5", lg: "size-6" }[size];
  return (
    <span className={cn("grid shrink-0 place-items-center", box, TILE_TONES[tone], className)} aria-hidden>
      <Icon className={glyph} strokeWidth={1.75} />
    </span>
  );
}

// Soft backgrounds for initials; the colour follows the name so a person keeps theirs.
const AVATAR_COLORS = [
  "bg-primary-100 text-primary-800",
  "bg-[#fde7d4] text-[#9a4a0b]",
  "bg-[#dcf5e7] text-[#166534]",
  "bg-[#ede4fd] text-[#5b21b6]",
  "bg-[#fde2e7] text-[#9f1239]",
];

function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  const first = words.length > 1 ? words[words.length - 2][0] : "";
  return (first + words[words.length - 1][0]).toUpperCase();
}

/** People have no photos in the demo data, so avatars show initials. */
export function Avatar({
  name,
  size = "md",
  shape = "circle",
  className,
}: {
  name: string;
  size?: "sm" | "md" | "lg";
  shape?: "circle" | "square";
  className?: string;
}) {
  const hash = [...name].reduce((sum, char) => sum + char.charCodeAt(0), 0);
  const box = { sm: "size-7 text-[11px]", md: "size-9 text-xs", lg: "size-11 text-sm" }[size];
  return (
    <span
      className={cn(
        "grid shrink-0 place-items-center font-semibold",
        shape === "circle" ? "rounded-full" : "rounded-lg",
        box,
        AVATAR_COLORS[hash % AVATAR_COLORS.length],
        className,
      )}
      aria-hidden
    >
      {initials(name)}
    </span>
  );
}
