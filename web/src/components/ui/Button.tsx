// Button - primary/secondary/ghost/danger variants; Figma: 50px high, 10px radius

import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "link";
type Size = "lg" | "md" | "sm";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  block?: boolean;
}

const VARIANTS: Record<Variant, string> = {
  primary: "bg-primary-600 text-white hover:bg-primary-700",
  secondary: "border border-line bg-white text-ink hover:border-primary-200 hover:bg-primary-50",
  ghost: "text-neutral-700 hover:bg-neutral-100",
  danger: "bg-danger-500 text-white hover:bg-danger-700",
  link: "px-0 text-primary-600 underline-offset-4 hover:underline",
};

const SIZES: Record<Size, string> = {
  lg: "h-[50px] px-6 text-base font-bold font-display",
  md: "h-10 px-4 text-sm font-semibold",
  sm: "h-8 px-3 text-xs font-semibold",
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  block = false,
  disabled,
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        "inline-flex items-center justify-center rounded-button transition-colors",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600",
        "disabled:cursor-not-allowed disabled:opacity-50",
        VARIANTS[variant],
        variant !== "link" && SIZES[size],
        variant === "link" && "h-auto text-sm font-semibold",
        block && "w-full",
        className,
      )}
      {...props}
    >
      {loading ? "Please wait..." : children}
    </button>
  );
}
