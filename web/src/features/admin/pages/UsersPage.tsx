// UsersPage - A-01 in the style of the Figma back office: account counters, one filter row,
// the user table with avatars; lock, unlock and reset password

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Lock, Truck, UserCog, Users } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { PageHeader } from "@/components/PageHeader";
import {
  Alert,
  Avatar,
  Badge,
  Button,
  Dialog,
  EmptyState,
  IconTile,
  Loading,
  Pagination,
  SelectField,
  Table,
  Td,
  TextField,
  Th,
} from "@/components/ui";
import { listHubs } from "@/features/auth/api";
import { errorMessage } from "@/lib/errors";
import { formatDateTime, formatPhone } from "@/lib/format";
import { useSession } from "@/lib/session";
import { toast } from "@/lib/toast";
import type { User } from "@/types";
import { listUsers, resetUserPassword, setUserLocked, type UserFilters } from "../api";
import { TemporaryPasswordDialog } from "../components/TemporaryPasswordDialog";
import { ROLE_OPTIONS, STATUS_OPTIONS, STATUS_TONE, roleLabel, statusLabel } from "../constants";

const PAGE_SIZE = 10;

const COUNTERS: { label: string; icon: typeof Users; filters: Partial<UserFilters>; tone: "primary" | "success" | "warning" | "danger" }[] = [
  { label: "All accounts", icon: Users, filters: {}, tone: "primary" },
  { label: "Drivers", icon: Truck, filters: { role: "DRIVER" }, tone: "success" },
  { label: "Hub managers", icon: UserCog, filters: { role: "HUB_MANAGER" }, tone: "warning" },
  { label: "Locked", icon: Lock, filters: { status: "LOCKED" }, tone: "danger" },
];

/** Account counters (one small count query each), drawn like the Figma report tiles. */
function Counter({ label, icon, filters, tone }: (typeof COUNTERS)[number]) {
  const count = useQuery({
    queryKey: ["admin", "users", "count", filters],
    queryFn: () => listUsers({ ...filters, page: 1, page_size: 1 }),
  });
  return (
    <section className="flex items-center gap-4 rounded-2xl border border-line/70 bg-white p-4 shadow-[0_4px_24px_rgba(15,23,42,0.05)]">
      <IconTile icon={icon} tone={tone} size="lg" />
      <div>
        <p className="text-[13px] text-neutral-600">{label}</p>
        <p className="text-2xl font-bold text-ink tabular-nums">{count.data?.total ?? "-"}</p>
      </div>
    </section>
  );
}

export function UsersPage() {
  const queryClient = useQueryClient();
  const me = useSession((state) => state.user);
  const [filters, setFilters] = useState<UserFilters>({ page: 1, page_size: PAGE_SIZE });
  const [search, setSearch] = useState("");
  const [confirmLock, setConfirmLock] = useState<User | null>(null);
  const [temporary, setTemporary] = useState<{ email: string; password: string } | null>(null);

  const hubs = useQuery({ queryKey: ["hubs"], queryFn: listHubs });
  const users = useQuery({
    queryKey: ["admin", "users", filters],
    queryFn: () => listUsers(filters),
    placeholderData: keepPreviousData,
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["admin", "users"] });

  const lock = useMutation({
    mutationFn: ({ user, locked }: { user: User; locked: boolean }) => setUserLocked(user.id, locked),
    onSuccess: (user) => {
      toast.success(`${user.full_name} is now ${statusLabel(user.status).toLowerCase()}.`);
      setConfirmLock(null);
      void refresh();
    },
    onError: (error) => {
      setConfirmLock(null);
      toast.error(errorMessage(error));
    },
  });

  const reset = useMutation({
    mutationFn: (user: User) => resetUserPassword(user.id).then((result) => ({ user, result })),
    onSuccess: ({ user, result }) => setTemporary({ email: user.email, password: result.temporary_password }),
    onError: (error) => toast.error(errorMessage(error)),
  });

  const setFilter = (key: keyof UserFilters, value: string) =>
    setFilters((current) => ({ ...current, [key]: value || undefined, page: 1 }));

  return (
    <>
      <PageHeader
        title="Users"
        description="Accounts of drivers, hub managers, executives and system admins."
        actions={
          <Link
            to="/admin/users/new"
            className="inline-flex h-10 items-center rounded-lg bg-primary-600 px-4 text-sm font-semibold text-white hover:bg-primary-700"
          >
            New user
          </Link>
        }
      />

      <div className="mb-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {COUNTERS.map((counter) => (
          <Counter key={counter.label} {...counter} />
        ))}
      </div>

      <form
        className="mb-4 grid gap-3 rounded-2xl border border-line/70 bg-white p-4 shadow-[0_4px_24px_rgba(15,23,42,0.05)] md:grid-cols-[2fr_1fr_1fr_1fr_auto]"
        onSubmit={(event) => {
          event.preventDefault();
          setFilter("q", search.trim());
        }}
      >
        <TextField compact placeholder="Search name, e-mail or phone" value={search} onChange={(event) => setSearch(event.target.value)} aria-label="Search" />
        <SelectField compact aria-label="Role" placeholder="All roles" options={ROLE_OPTIONS} value={filters.role ?? ""} onChange={(event) => setFilter("role", event.target.value)} />
        <SelectField
          compact
          aria-label="Hub"
          placeholder="All hubs"
          options={(hubs.data ?? []).map((hub) => ({ value: hub.id, label: hub.name }))}
          value={filters.hub_id ?? ""}
          onChange={(event) => setFilter("hub_id", event.target.value)}
        />
        <SelectField compact aria-label="Status" placeholder="All statuses" options={STATUS_OPTIONS} value={filters.status ?? ""} onChange={(event) => setFilter("status", event.target.value)} />
        <Button type="submit" variant="secondary">
          Search
        </Button>
      </form>

      {users.isError && <Alert tone="danger">{errorMessage(users.error)}</Alert>}
      {users.isPending && <Loading />}
      {users.data && users.data.items.length === 0 && <EmptyState title="No users match these filters" />}
      {users.data && users.data.items.length > 0 && (
        <>
          <Table>
            <thead>
              <tr>
                <Th>Name</Th>
                <Th>Contact</Th>
                <Th>Role</Th>
                <Th>Hub</Th>
                <Th>Status</Th>
                <Th>Last sign-in</Th>
                <Th className="text-right">Actions</Th>
              </tr>
            </thead>
            <tbody>
              {users.data.items.map((user) => (
                <tr key={user.id} className="hover:bg-neutral-50">
                  <Td>
                    <span className="flex items-center gap-3">
                      <Avatar name={user.full_name} />
                      <Link to={`/admin/users/${user.id}`} className="font-medium text-ink hover:text-primary-600">
                        {user.full_name}
                      </Link>
                    </span>
                  </Td>
                  <Td>
                    <span className="block">{user.email}</span>
                    <span className="text-xs text-neutral-600">{formatPhone(user.phone)}</span>
                  </Td>
                  <Td>{roleLabel(user.role)}</Td>
                  <Td>{user.hub_name ?? "-"}</Td>
                  <Td>
                    <Badge tone={STATUS_TONE[user.status]}>{statusLabel(user.status)}</Badge>
                  </Td>
                  <Td className="text-neutral-600">{formatDateTime(user.last_login_at)}</Td>
                  <Td className="text-right whitespace-nowrap">
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={user.id === me?.id}
                      onClick={() => setConfirmLock(user)}
                    >
                      {user.status === "LOCKED" ? "Unlock" : "Lock"}
                    </Button>
                    <Button variant="ghost" size="sm" disabled={reset.isPending} onClick={() => reset.mutate(user)}>
                      Reset password
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
          <Pagination
            page={users.data.page}
            pageSize={users.data.page_size}
            total={users.data.total}
            onChange={(page) => setFilters((current) => ({ ...current, page }))}
          />
        </>
      )}

      <Dialog
        open={Boolean(confirmLock)}
        title={confirmLock?.status === "LOCKED" ? "Unlock account?" : "Lock account?"}
        onClose={() => setConfirmLock(null)}
        actions={
          <>
            <Button variant="secondary" onClick={() => setConfirmLock(null)}>
              Cancel
            </Button>
            <Button
              variant={confirmLock?.status === "LOCKED" ? "primary" : "danger"}
              loading={lock.isPending}
              onClick={() => confirmLock && lock.mutate({ user: confirmLock, locked: confirmLock.status !== "LOCKED" })}
            >
              {confirmLock?.status === "LOCKED" ? "Unlock" : "Lock"}
            </Button>
          </>
        }
      >
        {confirmLock?.status === "LOCKED"
          ? `${confirmLock?.full_name} will be able to sign in again.`
          : `${confirmLock?.full_name} will be signed out on all devices and cannot sign in until unlocked.`}
      </Dialog>

      <TemporaryPasswordDialog
        password={temporary?.password ?? null}
        email={temporary?.email ?? ""}
        onClose={() => setTemporary(null)}
      />
    </>
  );
}
