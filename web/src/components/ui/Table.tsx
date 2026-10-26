// Table and Pagination - data tables for dashboards and the simulator

import type { ReactNode, TdHTMLAttributes, ThHTMLAttributes } from "react";
import { cn } from "@/lib/cn";
import { Button } from "./Button";

/** `framed` draws its own border; inside a Panel pass `framed={false}`. */
export function Table({ children, framed = true }: { children: ReactNode; framed?: boolean }) {
  return (
    <div
      className={cn(
        "overflow-x-auto bg-white",
        framed && "rounded-2xl border border-line/70 shadow-[0_4px_24px_rgba(15,23,42,0.05)]",
      )}
    >
      <table className="w-full min-w-[640px] border-collapse text-left text-sm">{children}</table>
    </div>
  );
}

// Figma tables: white header with small grey capitals, one hairline per row.
export function Th({ className, ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      scope="col"
      className={cn(
        "border-b border-line bg-white px-4 py-3.5 text-xs font-medium tracking-wide text-neutral-600 uppercase",
        className,
      )}
      {...props}
    />
  );
}

export function Td({ className, ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn("border-b border-line px-4 py-3.5 align-middle text-neutral-800", className)} {...props} />;
}

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onChange: (page: number) => void;
}

export function Pagination({ page, pageSize, total, onChange }: PaginationProps) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);
  return (
    <nav className="mt-4 flex items-center justify-between text-sm text-neutral-600" aria-label="Pagination">
      <span>
        {from}-{to} of {total}
      </span>
      <div className="flex items-center gap-2">
        <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => onChange(page - 1)}>
          Previous
        </Button>
        <span>
          Page {page} / {pages}
        </span>
        <Button variant="secondary" size="sm" disabled={page >= pages} onClick={() => onChange(page + 1)}>
          Next
        </Button>
      </div>
    </nav>
  );
}
