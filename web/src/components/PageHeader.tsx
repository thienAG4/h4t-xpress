// PageHeader - page title, short description and optional actions (Figma "Overview", "Reports").
// Back-office pages draw a divider under it, as in the Figma reports frame.

import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export function PageHeader({
  title,
  description,
  actions,
  divider = false,
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  divider?: boolean;
}) {
  return (
    <div className={cn("mb-6 flex flex-wrap items-end justify-between gap-4", divider && "border-b border-line pb-5")}>
      <div>
        <h1 className="font-sans text-2xl font-semibold text-ink">{title}</h1>
        {description && <p className="mt-1 text-sm text-neutral-600">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
