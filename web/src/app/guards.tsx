// Route guards - wait for the session, then check sign-in and permission

import type { ReactNode } from "react";
import { Navigate, Outlet, useLocation } from "react-router";
import { Loading } from "@/components/ui";
import { hasPermission, homePathFor, useSession } from "@/lib/session";

/** Pages behind sign-in. Without the permission the user goes to their own home page. */
export function RequireAuth({ permission, children }: { permission?: string; children?: ReactNode }) {
  const { status, user } = useSession();
  const location = useLocation();

  if (status === "loading") return <Loading label="Restoring your session..." />;
  if (status === "anonymous" || !user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (permission && !hasPermission(user, permission)) {
    return <Navigate to={homePathFor(user)} replace />;
  }
  return children ?? <Outlet />;
}

/** Sign-in pages: a signed-in user is sent to their home page instead. */
export function RedirectIfSignedIn({ children }: { children?: ReactNode }) {
  const { status, user } = useSession();
  if (status === "loading") return <Loading label="Restoring your session..." />;
  if (status === "authenticated") return <Navigate to={homePathFor(user)} replace />;
  return children ?? <Outlet />;
}
