// Shared navigation helpers for the dashboard shells: menu items filtered by permission, sign out

import { useMutation } from "@tanstack/react-query";
import type { LucideIcon } from "lucide-react";
import { useNavigate } from "react-router";
import { logout } from "@/features/auth/api";
import { hasPermission, useSession } from "@/lib/session";

export type NavItem = {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
  // The link is only shown to users holding this permission (menus follow RBAC).
  permission?: string;
};

export function useVisibleNav(items: NavItem[]): NavItem[] {
  const user = useSession((state) => state.user);
  return items.filter((item) => !item.permission || hasPermission(user, item.permission));
}

export function useSignOut() {
  const navigate = useNavigate();
  return useMutation({
    mutationFn: logout,
    onSettled: () => navigate("/login", { replace: true }),
  });
}
