// ScreenTitle - blue title bar of driver sub-screens (Figma "Order Details") with a Back link

import type { ReactNode } from "react";
import { Link } from "react-router";

export function ScreenTitle({ title, back, aside }: { title: string; back?: string; aside?: ReactNode }) {
  return (
    <div className="-mx-4 -mt-4 mb-4 flex h-12 items-center gap-3 bg-primary-600 px-4 text-white">
      {back && (
        <Link to={back} className="text-sm font-semibold text-white/90 hover:text-white">
          Back
        </Link>
      )}
      <h1 className="flex-1 truncate text-center font-display text-base font-bold">{title}</h1>
      <span className="min-w-9 text-right text-sm">{aside}</span>
    </div>
  );
}
