// Popover - a button that opens a small panel (top bar menus); closes on outside click or Escape

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";

export function Popover({
  label,
  button,
  buttonClassName,
  panelClassName,
  align = "end",
  children,
}: {
  /** Accessible name of the trigger button. */
  label: string;
  button: ReactNode;
  buttonClassName?: string;
  panelClassName?: string;
  align?: "start" | "end";
  children: (close: () => void) => ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const panelId = useId();

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={root} className="relative">
      <button
        type="button"
        aria-label={label}
        aria-expanded={open}
        aria-controls={panelId}
        className={buttonClassName}
        onClick={() => setOpen((value) => !value)}
      >
        {button}
      </button>
      {open && (
        <div
          id={panelId}
          className={cn(
            "absolute top-full z-[1100] mt-2 rounded-lg border border-line bg-white shadow-lg",
            align === "end" ? "right-0" : "left-0",
            panelClassName,
          )}
        >
          {children(() => setOpen(false))}
        </div>
      )}
    </div>
  );
}
