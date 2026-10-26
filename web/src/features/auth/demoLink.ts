// Demo deep link - maps the short role names used in /demo/:role links to role codes

import type { RoleCode } from "@/types";

// Short names keep links readable when they are shared, e.g. from a portfolio page.
export const DEMO_ROLE_SLUGS: Record<string, RoleCode> = {
  driver: "DRIVER",
  hub: "HUB_MANAGER",
  executive: "EXECUTIVE",
  admin: "SYSTEM_ADMIN",
};

/** Role code for a /demo/:role slug, or null when the slug is unknown. */
export function demoRoleFromSlug(slug: string | undefined): RoleCode | null {
  if (!slug) return null;
  return DEMO_ROLE_SLUGS[slug.toLowerCase()] ?? null;
}
