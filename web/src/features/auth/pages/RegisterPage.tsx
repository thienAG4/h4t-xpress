// RegisterPage - "Let's Get started" (D-01): driver sign-up, then OTP verification

import { useMutation, useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import { AuthHeading } from "@/app/layouts/AuthLayout";
import { Alert, Button, PasswordField, SelectField, TextField } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { ApiError } from "@/lib/http";
import { listHubs, registerDriver } from "../api";
import { normalizePhone, validateSignUp, type FormErrors, type SignUpForm } from "../validation";

const EMPTY: SignUpForm = {
  full_name: "",
  phone: "",
  email: "",
  password: "",
  confirm_password: "",
  hub_id: "",
  vehicle_plate: "",
  license_no: "",
};

export function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<SignUpForm>(EMPTY);
  const [errors, setErrors] = useState<FormErrors>({});
  const hubs = useQuery({ queryKey: ["hubs"], queryFn: listHubs });

  const mutation = useMutation({
    mutationFn: () =>
      registerDriver({
        full_name: form.full_name.trim(),
        phone: normalizePhone(form.phone),
        email: form.email.trim(),
        password: form.password,
        hub_id: form.hub_id,
        vehicle_plate: form.vehicle_plate.trim(),
        license_no: form.license_no.trim(),
      }),
    onSuccess: (sent) => navigate("/verify", { state: { phone: normalizePhone(form.phone), sent } }),
    onError: (error) => {
      if (error instanceof ApiError) setErrors(error.fieldErrors);
    },
  });

  const update = (field: keyof SignUpForm) => (value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: "" }));
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const found = validateSignUp(form);
    setErrors(found);
    if (Object.keys(found).length === 0) mutation.mutate();
  };

  return (
    <>
      <AuthHeading title="Let's Get started" subtitle="Sign up to enjoy the best benefits from the company." />
      <form className="flex flex-col gap-5" onSubmit={handleSubmit} noValidate>
        {mutation.isError && !(mutation.error instanceof ApiError && mutation.error.code === "VALIDATION_ERROR") && (
          <Alert tone="danger">{errorMessage(mutation.error)}</Alert>
        )}
        <TextField
          label="Your name"
          placeholder="Full name"
          autoComplete="name"
          value={form.full_name}
          error={errors.full_name}
          onChange={(event) => update("full_name")(event.target.value)}
        />
        <TextField
          label="Phone number"
          placeholder="Phone number"
          prefix="+84"
          inputMode="tel"
          autoComplete="tel"
          value={form.phone}
          error={errors.phone}
          onChange={(event) => update("phone")(event.target.value)}
        />
        <TextField
          label="E-mail"
          type="email"
          placeholder="name@example.com"
          autoComplete="email"
          value={form.email}
          error={errors.email}
          onChange={(event) => update("email")(event.target.value)}
        />
        <PasswordField
          label="Password"
          placeholder="Input password"
          autoComplete="new-password"
          hint="Must include letter, number and a character"
          value={form.password}
          error={errors.password}
          onChange={(event) => update("password")(event.target.value)}
        />
        <PasswordField
          label="Confirm password"
          placeholder="Re-enter password"
          autoComplete="new-password"
          value={form.confirm_password}
          error={errors.confirm_password}
          onChange={(event) => update("confirm_password")(event.target.value)}
        />

        <fieldset className="flex flex-col gap-5 border-t border-line pt-5">
          <legend className="pr-2 text-sm font-semibold">Work information</legend>
          <SelectField
            label="Hub"
            placeholder={hubs.isPending ? "Loading hubs..." : "Choose your hub"}
            value={form.hub_id}
            error={errors.hub_id}
            options={(hubs.data ?? []).map((hub) => ({ value: hub.id, label: hub.name }))}
            onChange={(event) => update("hub_id")(event.target.value)}
          />
          <TextField
            label="Vehicle plate"
            placeholder="59X1-123.45"
            value={form.vehicle_plate}
            error={errors.vehicle_plate}
            onChange={(event) => update("vehicle_plate")(event.target.value)}
          />
          <TextField
            label="Driving licence number"
            placeholder="790123456789"
            value={form.license_no}
            error={errors.license_no}
            onChange={(event) => update("license_no")(event.target.value)}
          />
        </fieldset>

        <Button type="submit" size="lg" block loading={mutation.isPending}>
          Get started
        </Button>
      </form>
      <p className="mt-6 text-center text-sm">
        Already have an account?{" "}
        <Link to="/login" className="font-semibold text-primary-600">
          Log In
        </Link>
      </p>
    </>
  );
}
