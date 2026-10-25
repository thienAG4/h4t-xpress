// Feedback components - Alert, Badge, Card, KpiCard, Loading and EmptyState

import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type Tone = "info" | "success" | "warning" | "danger" | "neutral" | "primary";

const TONES: Record<Tone, string> = {
  info: "bg-primary-50 text-primary-800 border-primary-100",
  primary: "bg-primary-50 text-primary-700 border-primary-100",
  success: "bg-success-50 text-success-700 border-success-50",
  warning: "bg-warning-50 text-warning-700 border-warning-50",
  danger: "bg-danger-50 text-danger-700 border-danger-50",
  neutral: "bg-neutral-100 text-neutral-700 border-neutral-200",
};

export function Alert({
  tone = "info",
  title,
  children,
  className,
}: {
  tone?: Tone;
  title?: string;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={cn("rounded-card border px-4 py-3 text-sm", TONES[tone], className)}
    >
      {title && <p className="font-semibold">{title}</p>}
      {children && <div className={cn(title && "mt-1")}>{children}</div>}
    </div>
  );
}

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        TONES[tone],
      )}
    >
      {children}
    </span>
  );
}

export function Card({
  title,
  actions,
  children,
  className,
}: {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("rounded-card border border-line bg-white p-5", className)}>
      {(title || actions) && (
        <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
          {title && <h2 className="text-base font-semibold">{title}</h2>}
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}

export function Loading({ label = "Loading..." }: { label?: string }) {
  return (
    <p role="status" className="animate-pulse py-8 text-center text-sm text-neutral-500">
      {label}
    </p>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-card border border-dashed border-neutral-300 bg-white px-6 py-10 text-center">
      <p className="font-semibold text-ink">{title}</p>
      {children && <div className="mt-2 text-sm text-neutral-600">{children}</div>}
    </div>
  );
}

export function KpiCard({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "neutral" | "danger" | "warning" | "success" | "primary";
}) {
  const accent = {
    neutral: "border-l-neutral-300",
    danger: "border-l-danger-500",
    warning: "border-l-warning-500",
    success: "border-l-success-500",
    primary: "border-l-primary-600",
  }[tone];
  return (
    <section className={cn("rounded-card border border-l-4 border-line bg-white px-5 py-4", accent)}>
      <p className="text-sm text-neutral-600">{label}</p>
      <p className="mt-1 font-display text-3xl font-bold text-ink">{value}</p>
      {hint && <p className="mt-1 text-xs text-neutral-600">{hint}</p>}
    </section>
  );
}
