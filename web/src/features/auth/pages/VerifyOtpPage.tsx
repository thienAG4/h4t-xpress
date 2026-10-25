// VerifyOtpPage - "Verify Your Number" (D-03): 6-digit code, resend with countdown

import { useMutation } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router";
import { AuthHeading } from "@/app/layouts/AuthLayout";
import { Alert, Button, TextField } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { ApiError } from "@/lib/http";
import { homePathFor } from "@/lib/session";
import { toast } from "@/lib/toast";
import type { OtpSent } from "@/types";
import { resendOtp, verifyOtp } from "../api";
import { OtpInput } from "../components/OtpInput";
import { isValidPhone, normalizePhone } from "../validation";

function secondsUntil(iso: string | undefined): number {
  return iso ? Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / 1000)) : 0;
}

export function VerifyOtpPage() {
  const navigate = useNavigate();
  const state = useLocation().state as { phone?: string; sent?: OtpSent } | null;
  const [phone, setPhone] = useState(state?.phone ?? "");
  const [sent, setSent] = useState<OtpSent | undefined>(state?.sent);
  const [code, setCode] = useState("");
  const [cooldown, setCooldown] = useState(() => secondsUntil(state?.sent?.resend_available_at));

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = window.setTimeout(() => setCooldown((value) => value - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [cooldown]);

  const verify = useMutation({
    mutationFn: () => verifyOtp(normalizePhone(phone), code),
    onSuccess: (response) => {
      toast.success("Phone number verified. Welcome to H4T Xpress!");
      navigate(homePathFor(response.user), { replace: true });
    },
  });

  const resend = useMutation({
    mutationFn: () => resendOtp(normalizePhone(phone)),
    onSuccess: (next) => {
      setSent(next);
      setCode("");
      setCooldown(secondsUntil(next.resend_available_at));
      toast.info("A new code has been sent.");
    },
    onError: (error) => {
      if (error instanceof ApiError && error.code === "OTP_COOLDOWN") {
        setCooldown((error.details as { retry_after_seconds?: number })?.retry_after_seconds ?? 60);
      }
      toast.error(errorMessage(error));
    },
  });

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (code.length === 6 && isValidPhone(phone)) verify.mutate();
  };

  const attemptsLeft =
    verify.error instanceof ApiError && verify.error.code === "OTP_INVALID"
      ? (verify.error.details as { attempts_left?: number } | undefined)?.attempts_left
      : undefined;

  return (
    <>
      <AuthHeading
        title="Verify Your Number"
        subtitle={sent ? `Enter the OTP sent to ${sent.phone_hint}` : "Enter the OTP sent to your phone"}
      />
      <form className="flex flex-col gap-6" onSubmit={handleSubmit} noValidate>
        {sent?.demo_code && (
          <Alert tone="warning" title="Demo environment">
            No SMS is sent. Your code is <strong className="font-display tracking-widest">{sent.demo_code}</strong>
          </Alert>
        )}
        {!state?.phone && (
          <TextField
            label="Phone number"
            prefix="+84"
            inputMode="tel"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
          />
        )}
        <OtpInput value={code} onChange={setCode} invalid={verify.isError} />
        {verify.isError && (
          <Alert tone="danger">
            {errorMessage(verify.error)}
            {attemptsLeft !== undefined && ` ${attemptsLeft} attempts left.`}
          </Alert>
        )}
        <Button type="submit" size="lg" block loading={verify.isPending} disabled={code.length !== 6}>
          Verify
        </Button>
      </form>
      <p className="mt-6 text-center text-sm">
        Didn&apos;t get the code?{" "}
        <Button
          variant="link"
          disabled={cooldown > 0 || resend.isPending || !isValidPhone(phone)}
          onClick={() => resend.mutate()}
        >
          {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend code"}
        </Button>
      </p>
    </>
  );
}
