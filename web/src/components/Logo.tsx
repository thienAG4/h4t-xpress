// Logo - "H4T Xpress" wordmark, the truck mark of the hub rail and the red back-office wordmark

import { cn } from "@/lib/cn";

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn("font-display text-lg font-extrabold tracking-tight text-ink", className)}>
      H4T <span className="text-primary-600">Xpress</span>
    </span>
  );
}

/** Truck with speed lines, as on the Figma hub screens. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 32" className={cn("h-8 w-12", className)} role="img" aria-label="H4T Xpress">
      <path d="M2 10h11M5 16h9M2 22h11" stroke="#ec8000" strokeWidth="2.6" strokeLinecap="round" />
      <rect x="16" y="5" width="18" height="17" rx="2.5" fill="#1070f8" />
      <path d="M34 10h5.5a2 2 0 0 1 1.6.8l4.4 5.9a2 2 0 0 1 .4 1.2V22H34z" fill="#0b5ad0" />
      <path d="M36.5 12.5h3.4l2.7 3.6h-6.1z" fill="#d4e4fe" />
      <circle cx="22" cy="24.5" r="3.6" fill="#fff" stroke="#0a479f" strokeWidth="2.4" />
      <circle cx="39" cy="24.5" r="3.6" fill="#fff" stroke="#0a479f" strokeWidth="2.4" />
    </svg>
  );
}

/** Figma "Nhà quản trị" pages print the brand in red capitals. */
export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn("font-display text-[17px] font-extrabold tracking-wide text-danger-500 uppercase", className)}>
      H4T Xpress
    </span>
  );
}
