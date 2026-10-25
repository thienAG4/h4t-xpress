// DemoLoginPanel - one-click sign-in per role, shown only when the API runs in demo mode

import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { Button } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { homePathFor } from "@/lib/session";
import { toast } from "@/lib/toast";
import type { RoleCode } from "@/types";
import { demoLogin } from "../api";

const ROLES: { role: RoleCode; label: string }[] = [
  { role: "DRIVER", label: "Driver" },
  { role: "HUB_MANAGER", label: "Hub Manager" },
  { role: "EXECUTIVE", label: "Executive" },
  { role: "SYSTEM_ADMIN", label: "System Admin" },
];

export function DemoLoginPanel() {
  const navigate = useNavigate();
  const mutation = useMutation({
    mutationFn: demoLogin,
    onSuccess: (response) => navigate(homePathFor(response.user), { replace: true }),
    onError: (error) => toast.error(errorMessage(error)),
  });

  return (
    <section className="mt-8 rounded-card border border-dashed border-primary-200 bg-primary-50 p-4">
      <h2 className="text-sm font-semibold text-primary-800">Quick demo login</h2>
      <p className="mt-1 text-xs text-primary-800">Sign in as a shared demo account of each role.</p>
      <div className="mt-3 grid grid-cols-2 gap-2">
        {ROLES.map(({ role, label }) => (
          <Button
            key={role}
            variant="secondary"
            size="sm"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate(role)}
          >
            {label}
          </Button>
        ))}
      </div>
    </section>
  );
}
