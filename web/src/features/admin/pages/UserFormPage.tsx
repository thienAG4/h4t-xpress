// UserFormPage - A-02: create an account, or edit one (route /admin/users/:userId)

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { PageHeader } from "@/components/PageHeader";
import { Alert, Button, Card, Loading, PasswordField, SelectField, TextField } from "@/components/ui";
import { listHubs } from "@/features/auth/api";
import { isValidEmail, isValidPhone, normalizePhone, passwordProblem } from "@/features/auth/validation";
import { errorMessage } from "@/lib/errors";
import { ApiError } from "@/lib/http";
import { toast } from "@/lib/toast";
import type { RoleCode, User, UserCreateInput } from "@/types";
import { createUser, getUser, updateUser } from "../api";
import { TemporaryPasswordDialog } from "../components/TemporaryPasswordDialog";
import { ROLE_OPTIONS, ROLES_WITH_HUB } from "../constants";

type FormState = {
  full_name: string;
  email: string;
  phone: string;
  role: string;
  hub_id: string;
  password: string;
  vehicle_plate: string;
  license_no: string;
  address: string;
};

const EMPTY: FormState = {
  full_name: "",
  email: "",
  phone: "",
  role: "HUB_MANAGER",
  hub_id: "",
  password: "",
  vehicle_plate: "",
  license_no: "",
  address: "",
};

function fromUser(user: User): FormState {
  return {
    full_name: user.full_name,
    email: user.email,
    phone: user.phone ?? "",
    role: user.role,
    hub_id: user.hub_id ?? "",
    password: "",
    vehicle_plate: user.driver?.vehicle_plate ?? "",
    license_no: user.driver?.license_no ?? "",
    address: user.address ?? "",
  };
}

function validate(form: FormState, isNew: boolean): Record<string, string> {
  const errors: Record<string, string> = {};
  if (form.full_name.trim().length < 2) errors.full_name = "Please enter the full name";
  if (!isValidEmail(form.email)) errors.email = "Please enter a valid e-mail";
  if (form.phone && !isValidPhone(form.phone)) errors.phone = "10 digits starting with 0, or +84";
  if (ROLES_WITH_HUB.has(form.role) && !form.hub_id) errors.hub_id = "A hub is required for this role";
  if (isNew && form.role === "DRIVER") {
    if (!form.vehicle_plate.trim()) errors.vehicle_plate = "Required for drivers";
    if (!form.license_no.trim()) errors.license_no = "Required for drivers";
  }
  if (isNew && form.password) {
    const problem = passwordProblem(form.password);
    if (problem) errors.password = problem;
  }
  return errors;
}

/** Loads the user when editing, then renders the form with its initial values. */
export function UserFormPage() {
  const { userId } = useParams();
  const existing = useQuery({
    queryKey: ["admin", "users", userId],
    queryFn: () => getUser(userId as string),
    enabled: Boolean(userId),
  });

  if (!userId) return <UserForm initial={EMPTY} />;
  if (existing.isPending) return <Loading />;
  if (existing.isError) return <Alert tone="danger">{errorMessage(existing.error)}</Alert>;
  return <UserForm key={userId} user={existing.data} initial={fromUser(existing.data)} />;
}

function UserForm({ user, initial }: { user?: User; initial: FormState }) {
  const isNew = !user;
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<FormState>(initial);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [created, setCreated] = useState<{ email: string; password: string } | null>(null);
  const hubs = useQuery({ queryKey: ["hubs"], queryFn: listHubs });

  const save = useMutation({
    mutationFn: async () => {
      const common = {
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        phone: form.phone ? normalizePhone(form.phone) : null,
        hub_id: ROLES_WITH_HUB.has(form.role) ? form.hub_id : null,
        address: form.address.trim() || null,
        vehicle_plate: form.vehicle_plate.trim() || null,
        license_no: form.license_no.trim() || null,
      };
      if (!user) {
        const body: UserCreateInput = { ...common, role: form.role as RoleCode, password: form.password || null };
        return createUser(body);
      }
      const updated = await updateUser(user.id, { ...common, role: form.role as RoleCode });
      return { user: updated, temporary_password: null };
    },
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      if (result.temporary_password) {
        setCreated({ email: result.user.email, password: result.temporary_password });
        return;
      }
      toast.success(isNew ? "User created." : "Changes saved.");
      navigate("/admin");
    },
    onError: (error) => {
      if (error instanceof ApiError) setErrors(error.fieldErrors);
    },
  });

  const update = (field: keyof FormState) => (value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: "" }));
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const found = validate(form, isNew);
    setErrors(found);
    if (Object.keys(found).length === 0) save.mutate();
  };

  const isDriver = form.role === "DRIVER";
  // Switching to or from the driver role is not supported by the API.
  const roleOptions = isNew ? ROLE_OPTIONS : ROLE_OPTIONS.filter((role) => (role.value === "DRIVER") === isDriver);

  return (
    <>
      <PageHeader
        title={isNew ? "New user" : `Edit ${user.full_name}`}
        description={isNew ? "Leave the password empty to generate a temporary one." : undefined}
        actions={
          <Link to="/admin" className="text-sm font-semibold text-primary-600">
            Back to users
          </Link>
        }
      />
      <Card className="max-w-2xl">
        <form className="grid gap-5 md:grid-cols-2" onSubmit={handleSubmit} noValidate>
          {save.isError && !(save.error instanceof ApiError && save.error.code === "VALIDATION_ERROR") && (
            <Alert tone="danger" className="md:col-span-2">
              {errorMessage(save.error)}
            </Alert>
          )}
          <TextField compact label="Full name" value={form.full_name} error={errors.full_name} onChange={(event) => update("full_name")(event.target.value)} />
          <TextField compact label="E-mail" type="email" value={form.email} error={errors.email} onChange={(event) => update("email")(event.target.value)} />
          <TextField compact label="Phone (optional)" inputMode="tel" value={form.phone} error={errors.phone} onChange={(event) => update("phone")(event.target.value)} />
          <SelectField
            compact
            label="Role"
            options={roleOptions}
            value={form.role}
            disabled={!isNew && isDriver}
            onChange={(event) => update("role")(event.target.value)}
          />
          {ROLES_WITH_HUB.has(form.role) && (
            <SelectField
              compact
              label="Hub"
              placeholder="Choose a hub"
              options={(hubs.data ?? []).map((hub) => ({ value: hub.id, label: hub.name }))}
              value={form.hub_id}
              error={errors.hub_id}
              onChange={(event) => update("hub_id")(event.target.value)}
            />
          )}
          {isDriver && (
            <>
              <TextField compact label="Vehicle plate" value={form.vehicle_plate} error={errors.vehicle_plate} onChange={(event) => update("vehicle_plate")(event.target.value)} />
              <TextField compact label="Licence number" value={form.license_no} error={errors.license_no} onChange={(event) => update("license_no")(event.target.value)} />
            </>
          )}
          <TextField compact label="Address (optional)" value={form.address} onChange={(event) => update("address")(event.target.value)} />
          {isNew && (
            <PasswordField
              compact
              label="Password (optional)"
              hint="Leave empty to generate one"
              autoComplete="new-password"
              value={form.password}
              error={errors.password}
              onChange={(event) => update("password")(event.target.value)}
            />
          )}
          <div className="flex justify-end gap-2 md:col-span-2">
            <Button variant="secondary" onClick={() => navigate("/admin")}>
              Cancel
            </Button>
            <Button type="submit" loading={save.isPending}>
              {isNew ? "Create user" : "Save changes"}
            </Button>
          </div>
        </form>
      </Card>
      <TemporaryPasswordDialog
        password={created?.password ?? null}
        email={created?.email ?? ""}
        onClose={() => {
          setCreated(null);
          navigate("/admin");
        }}
      />
    </>
  );
}
