import { Truck } from "lucide-react";
import { cn } from "@/lib/cn";

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2 font-display font-semibold", className)}>
      <span className="grid size-8 place-items-center rounded-control bg-primary-600 text-white">
        <Truck className="size-4" aria-hidden />
      </span>
      <span>
        H4T <span className="text-primary-600">Xpress</span>
      </span>
    </span>
  );
}
