// Admin API - users (A-01, A-02), role matrix (A-03), hubs, shifts, settings, audit (A-04..A-07)

import { request } from "@/lib/http";
import type {
  AdminArea,
  AdminHub,
  AdminShift,
  AreaInput,
  AuditEntry,
  HubInput,
  Page,
  Permission,
  Role,
  Setting,
  ShiftUpdateInput,
  User,
  UserCreateInput,
  UserUpdateInput,
} from "@/types";

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

// =============================== Configuration (A-04..A-07) ===============================

export function listAreas(): Promise<AdminArea[]> {
  return request<AdminArea[]>("/admin/areas");
}

export function saveArea(data: AreaInput, areaId?: string): Promise<AdminArea> {
  return areaId
    ? request<AdminArea>(`/admin/areas/${areaId}`, { method: "PUT", body: data })
    : request<AdminArea>("/admin/areas", { method: "POST", body: data });
}

export function listAdminHubs(): Promise<AdminHub[]> {
  return request<AdminHub[]>("/admin/hubs");
}

export function saveHub(data: HubInput, hubId?: string): Promise<AdminHub> {
  return hubId
    ? request<AdminHub>(`/admin/hubs/${hubId}`, { method: "PUT", body: data })
    : request<AdminHub>("/admin/hubs", { method: "POST", body: data });
}

export function listShifts(hubId?: string): Promise<AdminShift[]> {
  return request<AdminShift[]>("/admin/shifts", { query: { hub_id: hubId } });
}

export function updateShift(shiftId: string, data: ShiftUpdateInput): Promise<AdminShift> {
  return request<AdminShift>(`/admin/shifts/${shiftId}`, { method: "PATCH", body: data });
}

export function listSettings(): Promise<Setting[]> {
  return request<Setting[]>("/admin/settings");
}

export function updateSetting(key: string, value: unknown): Promise<Setting> {
  return request<Setting>(`/admin/settings/${key}`, { method: "PUT", body: { value } });
}

export type AuditFilters = { page: number; page_size: number; action?: string; entity_type?: string };

export function listAuditLogs(filters: AuditFilters): Promise<Page<AuditEntry>> {
  return request<Page<AuditEntry>>("/admin/audit-logs", { query: filters });
}
