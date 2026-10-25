// Session store - access token in memory, signed-in user and permission helpers

import { create } from "zustand";
import type { Me } from "@/types";

type SessionStatus = "loading" | "authenticated" | "anonymous";

interface SessionState {
  status: SessionStatus;
  accessToken: string | null;
  user: Me | null;
  setSession: (accessToken: string, user: Me) => void;
  setUser: (user: Me) => void;
  clear: () => void;
}

// The access token never touches localStorage; the refresh token is an httpOnly cookie.
export const useSession = create<SessionState>()((set) => ({
  status: "loading",
  accessToken: null,
  user: null,
  setSession: (accessToken, user) => set({ status: "authenticated", accessToken, user }),
  setUser: (user) => set({ user }),
  clear: () => set({ status: "anonymous", accessToken: null, user: null }),
}));

export function hasPermission(user: Me | null, permission: string): boolean {
  return Boolean(user?.permissions.includes(permission));
}

/** Landing page of each role after sign-in. */
export function homePathFor(user: Me | null): string {
  switch (user?.role) {
    case "DRIVER":
      return "/driver";
    case "HUB_MANAGER":
      return "/hub";
    case "EXECUTIVE":
      return "/reports";
    case "SYSTEM_ADMIN":
      return "/admin";
    default:
      return "/";
  }
}
