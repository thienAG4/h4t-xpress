// AuthLayout - centred mobile-width column used by sign-in screens (Figma 375px frames)

import { Link, Outlet } from "react-router";
import { Logo } from "@/components/Logo";

export function AuthLayout() {
  return (
    <div className="flex min-h-full flex-col items-center bg-white px-5 py-8 sm:bg-neutral-50 sm:py-12">
      <Link to="/" className="mb-8" aria-label="H4T Xpress home">
        <Logo />
      </Link>
      <main className="w-full max-w-[375px] sm:rounded-sheet sm:border sm:border-line sm:bg-white sm:px-6 sm:py-8">
        <Outlet />
      </main>
    </div>
  );
}

/** Title block of an auth screen: Montserrat bold 18px in the primary colour (Figma). */
export function AuthHeading({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-8 text-center">
      <h1 className="text-lg font-bold text-primary-600">{title}</h1>
      {subtitle && <p className="mt-2 font-display text-sm font-medium text-ink">{subtitle}</p>}
    </div>
  );
}
