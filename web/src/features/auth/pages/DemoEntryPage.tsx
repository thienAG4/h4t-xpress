// DemoEntryPage - /demo/:role signs in as that role's demo account and opens its home page.
// Used by links and embeds outside the app (portfolio), so a visitor skips the login form.

import { useMutation } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { Button } from "@/components/ui";
import { useHealth } from "@/features/system/useHealth";
import { errorMessage } from "@/lib/errors";
import { homePathFor, useSession } from "@/lib/session";
import { demoLogin } from "../api";
import { demoRoleFromSlug } from "../demoLink";

export function DemoEntryPage() {
  const { role: slug } = useParams();
  const role = demoRoleFromSlug(slug);
  const navigate = useNavigate();
  const sessionStatus = useSession((state) => state.status);
  const health = useHealth();
  const started = useRef(false);

  const mutation = useMutation({
    mutationFn: demoLogin,
    onSuccess: (response) => navigate(homePathFor(response.user), { replace: true }),
  });

  // Wait for the start-up session restore, otherwise it could finish later and bring back
  // an older session over the demo one.
  const ready = role !== null && sessionStatus !== "loading" && health.data?.demo_mode === true;
  useEffect(() => {
    if (!ready || role === null || started.current) return;
    started.current = true;
    mutation.mutate(role);
  }, [ready, role, mutation]);

  let message = "Signing in to the demo...";
  let failed = false;
  if (role === null) {
    message = `"${slug}" is not a demo role. Try driver, hub, executive or admin.`;
    failed = true;
  } else if (health.isError) {
    message = "The demo server could not be reached.";
    failed = true;
  } else if (health.data && !health.data.demo_mode) {
    message = "Demo sign-in is turned off on this server.";
    failed = true;
  } else if (mutation.isError) {
    message = errorMessage(mutation.error);
    failed = true;
  } else if (health.isPending) {
    // Free-tier hosting sleeps when idle; the first request can take up to a minute.
    message = "Waking up the demo server. Free hosting sleeps when idle, this can take up to a minute.";
  }

  return (
    <div className="grid min-h-dvh place-items-center bg-neutral-50 px-6 text-center">
      <div className="max-w-sm">
        <p className="text-sm font-semibold text-primary-600">H4T Xpress demo</p>
        <p role="status" className={failed ? "mt-3 text-sm text-danger-700" : "mt-3 animate-pulse text-sm text-neutral-600"}>
          {message}
        </p>
        {failed && (
          <div className="mt-6 flex justify-center gap-3">
            {role !== null && (
              <Button variant="secondary" size="sm" onClick={() => window.location.reload()}>
                Try again
              </Button>
            )}
            <Link to="/login" className="self-center text-sm font-medium text-primary-600">
              Go to sign-in
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
