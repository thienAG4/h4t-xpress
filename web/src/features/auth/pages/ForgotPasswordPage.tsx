// ForgotPasswordPage - request a reset code, then set a new password with it

import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import { AuthHeading } from "@/app/layouts/AuthLayout";
import { Alert, Button, PasswordField, TextField } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { toast } from "@/lib/toast";
import { forgotPassword, resetPassword, type ForgotPasswordResult } from "../api";
import { OtpInput } from "../components/OtpInput";
import { normalizePhone, passwordProblem } from "../validation";

export function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState("");
  const [result, setResult] = useState<ForgotPasswordResult>();
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string>();

  const normalized = identifier.includes("@") ? identifier.trim() : normalizePhone(identifier);

  const request = useMutation({
    mutationFn: () => forgotPassword(normalized),
    onSuccess: setResult,
  });

  const reset = useMutation({
    mutationFn: () => resetPassword(normalized, code, password),
    onSuccess: () => {
      toast.success("Password changed. Please sign in with your new password.");
      navigate("/login", { replace: true });
    },
  });

  const submitRequest = (event: FormEvent) => {
    event.preventDefault();
    if (identifier.trim()) request.mutate();
  };

  const submitReset = (event: FormEvent) => {
    event.preventDefault();
    const problem = passwordProblem(password);
    setPasswordError(problem ?? undefined);
    if (!problem && code.length === 6) reset.mutate();
  };

  return (
    <>
      <AuthHeading title="Reset Password" subtitle="We will send a code to the phone number of your account" />
      {!result ? (
        <form className="flex flex-col gap-5" onSubmit={submitRequest} noValidate>
          {request.isError && <Alert tone="danger">{errorMessage(request.error)}</Alert>}
          <TextField
            label="Phone number or e-mail"
            value={identifier}
            onChange={(event) => setIdentifier(event.target.value)}
          />
          <Button type="submit" size="lg" block loading={request.isPending} disabled={!identifier.trim()}>
            Send code
          </Button>
        </form>
      ) : (
        <form className="flex flex-col gap-5" onSubmit={submitReset} noValidate>
          <Alert tone="info">
            If an account exists for this phone or e-mail, a code has been sent
            {result.phone_hint ? ` to ${result.phone_hint}` : ""}.
          </Alert>
          {result.demo_code && (
            <Alert tone="warning" title="Demo environment">
              No SMS is sent. Your code is <strong className="font-display tracking-widest">{result.demo_code}</strong>
            </Alert>
          )}
          <OtpInput value={code} onChange={setCode} invalid={reset.isError} />
          <PasswordField
            label="New password"
            hint="Must include letter, number and a character"
            autoComplete="new-password"
            value={password}
            error={passwordError}
            onChange={(event) => setPassword(event.target.value)}
          />
          {reset.isError && <Alert tone="danger">{errorMessage(reset.error)}</Alert>}
          <Button type="submit" size="lg" block loading={reset.isPending} disabled={code.length !== 6}>
            Change password
          </Button>
        </form>
      )}
      <p className="mt-6 text-center text-sm">
        <Link to="/login" className="font-semibold text-primary-600">
          Back to Log In
        </Link>
      </p>
    </>
  );
}
