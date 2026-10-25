// ProfilePage - D-15: driver details, change password and sign out

import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { Alert, Button, Card, PasswordField } from "@/components/ui";
import { changePassword, logout } from "@/features/auth/api";
import { passwordProblem } from "@/features/auth/validation";
import { errorMessage } from "@/lib/errors";
import { formatPhone } from "@/lib/format";
import { useSession } from "@/lib/session";
import { toast } from "@/lib/toast";

export function ProfilePage() {
  const navigate = useNavigate();
  const user = useSession((state) => state.user);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [nextError, setNextError] = useState<string>();

  const change = useMutation({
    mutationFn: () => changePassword(current, next),
    onSuccess: () => {
      toast.success("Password changed.");
      setCurrent("");
      setNext("");
    },
  });

  const signOut = useMutation({
    mutationFn: logout,
    onSettled: () => navigate("/login", { replace: true }),
  });

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const problem = passwordProblem(next);
    setNextError(problem ?? undefined);
    if (!problem) change.mutate();
  };

  if (!user) return null;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-bold">Profile</h1>
      <Card>
        <dl className="grid grid-cols-[120px_1fr] gap-y-2 text-sm">
          <dt className="text-neutral-600">Name</dt>
          <dd className="font-medium">{user.full_name}</dd>
          <dt className="text-neutral-600">Phone</dt>
          <dd>{formatPhone(user.phone)}</dd>
          <dt className="text-neutral-600">E-mail</dt>
          <dd className="break-all">{user.email}</dd>
          <dt className="text-neutral-600">Hub</dt>
          <dd>{user.hub_name ?? "-"}</dd>
          <dt className="text-neutral-600">Vehicle</dt>
          <dd>{user.driver?.vehicle_plate ?? "-"}</dd>
          <dt className="text-neutral-600">Rating</dt>
          <dd>{user.driver ? `${Number(user.driver.rating).toFixed(2)} / 5` : "-"}</dd>
        </dl>
      </Card>

      <Card title="Change password">
        <form className="flex flex-col gap-4" onSubmit={handleSubmit} noValidate>
          {change.isError && <Alert tone="danger">{errorMessage(change.error)}</Alert>}
          <PasswordField
            label="Current password"
            autoComplete="current-password"
            value={current}
            onChange={(event) => setCurrent(event.target.value)}
          />
          <PasswordField
            label="New password"
            autoComplete="new-password"
            hint="Must include letter, number and a character"
            value={next}
            error={nextError}
            onChange={(event) => setNext(event.target.value)}
          />
          <Button type="submit" loading={change.isPending} disabled={!current || !next}>
            Save password
          </Button>
        </form>
      </Card>

      <Button variant="secondary" block loading={signOut.isPending} onClick={() => signOut.mutate()}>
        Sign out
      </Button>
    </div>
  );
}
