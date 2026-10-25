// RolesPage - A-03: role x permission matrix, saved per changed role (FR-A-02)

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Alert, Button, Loading, Table, Td, Th } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { toast } from "@/lib/toast";
import { listPermissions, listRoles, updateRolePermissions } from "../api";

const GROUP_LABEL: Record<string, string> = {
  driver: "Driver app",
  hub: "Hub operations",
  report: "Reports",
  admin: "System administration",
};

export function RolesPage() {
  const queryClient = useQueryClient();
  const roles = useQuery({ queryKey: ["admin", "roles"], queryFn: listRoles });
  const permissions = useQuery({ queryKey: ["admin", "permissions"], queryFn: listPermissions });
  // Only roles the admin has touched are kept here; untouched roles use the saved data.
  const [edits, setEdits] = useState<Record<string, Set<string>>>({});
  const [forceRelogin, setForceRelogin] = useState(true);

  const draft = useMemo(
    () =>
      Object.fromEntries(
        (roles.data ?? []).map((role) => [role.id, edits[role.id] ?? new Set(role.permissions)]),
      ),
    [roles.data, edits],
  );

  const changedRoles = useMemo(
    () =>
      (roles.data ?? []).filter((role) => {
        const current = draft[role.id];
        return current && (current.size !== role.permissions.length || role.permissions.some((code) => !current.has(code)));
      }),
    [roles.data, draft],
  );

  const save = useMutation({
    mutationFn: () =>
      Promise.all(changedRoles.map((role) => updateRolePermissions(role.id, [...draft[role.id]], forceRelogin))),
    onSuccess: (updated) => {
      toast.success(`Permissions saved for ${updated.map((role) => role.name).join(", ")}.`);
      setEdits({});
      void queryClient.invalidateQueries({ queryKey: ["admin", "roles"] });
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const toggle = (roleId: string, code: string) =>
    setEdits((current) => {
      const next = new Set(draft[roleId]);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return { ...current, [roleId]: next };
    });

  if (roles.isPending || permissions.isPending) return <Loading />;
  if (roles.isError || permissions.isError) {
    return <Alert tone="danger">{errorMessage(roles.error ?? permissions.error)}</Alert>;
  }

  const groups = Object.entries(
    permissions.data.reduce<Record<string, typeof permissions.data>>((acc, permission) => {
      (acc[permission.group] ??= []).push(permission);
      return acc;
    }, {}),
  );

  return (
    <>
      <PageHeader
        title="Roles & permissions"
        description="Tick what each role may do. The API checks these permission codes on every request."
        actions={
          <>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={forceRelogin} onChange={(event) => setForceRelogin(event.target.checked)} />
              Sign affected users out
            </label>
            <Button disabled={changedRoles.length === 0} loading={save.isPending} onClick={() => save.mutate()}>
              Save changes{changedRoles.length ? ` (${changedRoles.length})` : ""}
            </Button>
          </>
        }
      />
      <Table>
        <thead>
          <tr>
            <Th className="w-1/2">Permission</Th>
            {roles.data.map((role) => (
              <Th key={role.id} className="text-center">
                {role.name}
                <span className="block text-[11px] font-normal tracking-normal normal-case">{role.user_count} users</span>
              </Th>
            ))}
          </tr>
        </thead>
        <tbody>
          {groups.map(([group, items]) => (
            <GroupRows
              key={group}
              label={GROUP_LABEL[group] ?? group}
              items={items}
              roles={roles.data}
              draft={draft}
              onToggle={toggle}
            />
          ))}
        </tbody>
      </Table>
      <p className="mt-3 text-xs text-neutral-600">
        System Admin always keeps user and role management so the matrix can never be locked.
      </p>
    </>
  );
}

interface GroupRowsProps {
  label: string;
  items: { code: string; description: string }[];
  roles: { id: string; name: string }[];
  draft: Record<string, Set<string>>;
  onToggle: (roleId: string, code: string) => void;
}

function GroupRows({ label, items, roles, draft, onToggle }: GroupRowsProps) {
  return (
    <>
      <tr>
        <Td colSpan={roles.length + 1} className="bg-neutral-50 text-xs font-semibold tracking-wide text-neutral-600 uppercase">
          {label}
        </Td>
      </tr>
      {items.map((permission) => (
        <tr key={permission.code}>
          <Td>
            <span className="block font-medium">{permission.description}</span>
            <code className="text-xs text-neutral-500">{permission.code}</code>
          </Td>
          {roles.map((role) => (
            <Td key={role.id} className="text-center">
              <input
                type="checkbox"
                className="size-4 accent-primary-600"
                aria-label={`${role.name}: ${permission.description}`}
                checked={draft[role.id]?.has(permission.code) ?? false}
                onChange={() => onToggle(role.id, permission.code)}
              />
            </Td>
          ))}
        </tr>
      ))}
    </>
  );
}
