// LoginPage - "Welcome Back" (D-02): phone or e-mail + password, demo quick login

import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router";
import { AuthHeading } from "@/app/layouts/AuthLayout";
import { Alert, Button, PasswordField, TextField } from "@/components/ui";
import { useDemoMode } from "@/features/system/useHealth";
import { errorCode, errorMessage } from "@/lib/errors";
import { homePathFor } from "@/lib/session";
import { login } from "../api";
import { DemoLoginPanel } from "../components/DemoLoginPanel";
import { isValidEmail, isValidPhone, normalizePhone } from "../validation";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const demoMode = useDemoMode();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [fieldError, setFieldError] = useState<string>();
  const from = (location.state as { from?: string } | null)?.from;

  const mutation = useMutation({
    mutationFn: () => {
      const value = identifier.includes("@") ? identifier.trim() : normalizePhone(identifier);
      return login(value, password);
    },
    onSuccess: (response) => navigate(from ?? homePathFor(response.user), { replace: true }),
  });

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!isValidEmail(identifier) && !isValidPhone(identifier)) {
      setFieldError("Enter a phone number (0xxxxxxxxx or +84) or an e-mail");
      return;
    }
    setFieldError(undefined);
    mutation.mutate();
  };

  const notVerified = errorCode(mutation.error) === "ACCOUNT_NOT_VERIFIED";

  return (
    <>
      <AuthHeading title="Welcome Back" subtitle="Log in and pick up right where you left" />
      <form className="flex flex-col gap-5" onSubmit={handleSubmit} noValidate>
        {mutation.isError && (
          <Alert tone="danger">
            {errorMessage(mutation.error)}
            {notVerified && (
              <>
                {" "}
                <Link to="/verify" state={{ phone: normalizePhone(identifier) }} className="font-semibold underline">
                  Verify now
                </Link>
              </>
            )}
          </Alert>
        )}
        <TextField
          label="Phone number or e-mail"
          placeholder="0912 345 678 or name@example.com"
          autoComplete="username"
          value={identifier}
          error={fieldError}
          onChange={(event) => setIdentifier(event.target.value)}
        />
        <div className="flex flex-col gap-2">
          <PasswordField
            label="Password"
            placeholder="Input password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <Link to="/forgot-password" className="self-start text-xs text-ink hover:text-primary-600">
            Forgot password?
          </Link>
        </div>
        <Button type="submit" size="lg" block loading={mutation.isPending} disabled={!identifier || !password}>
          Log In
        </Button>
      </form>
      <p className="mt-6 text-center text-sm">
        Don&apos;t have an account?{" "}
        <Link to="/register" className="font-semibold text-primary-600">
          Create Account
        </Link>
      </p>
      {demoMode && <DemoLoginPanel />}
    </>
  );
}
