// Admin API - user accounts (A-01, A-02) and the role-permission matrix (A-03)

import { request } from "@/lib/http";
import type { Page, Permission, Role, User, UserCreateInput, UserUpdateInput } from "@/types";

export type UserFilters = {
  q?: string;
  role?: string;
  hub_id?: string;
  status?: string;
  page: number;
  page_size: number;
};

export function listUsers(filters: UserFilters): Promise<Page<User>> {
  return request<Page<User>>("/admin/users", { query: filters });
}

export function getUser(userId: string): Promise<User> {
  return request<User>(`/admin/users/${userId}`);
}

export function createUser(data: UserCreateInput): Promise<{ user: User; temporary_password: string | null }> {
  return request("/admin/users", { method: "POST", body: data });
}

export function updateUser(userId: string, data: UserUpdateInput): Promise<User> {
  return request<User>(`/admin/users/${userId}`, { method: "PATCH", body: data });
}

export function setUserLocked(userId: string, locked: boolean): Promise<User> {
  return request<User>(`/admin/users/${userId}/${locked ? "lock" : "unlock"}`, { method: "POST" });
}

export function resetUserPassword(userId: string): Promise<{ temporary_password: string }> {
  return request(`/admin/users/${userId}/reset-password`, { method: "POST" });
}

export function listRoles(): Promise<Role[]> {
  return request<Role[]>("/admin/roles");
}

export function listPermissions(): Promise<Permission[]> {
  return request<Permission[]>("/admin/permissions");
}

export function updateRolePermissions(roleId: string, permissions: string[], forceRelogin: boolean): Promise<Role> {
  return request<Role>(`/admin/roles/${roleId}/permissions`, {
    method: "PUT",
    body: { permissions, force_relogin: forceRelogin },
  });
}
