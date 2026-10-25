// Admin constants - labels and badge tones for roles and account statuses

export const ROLE_OPTIONS = [
  { value: "DRIVER", label: "Driver" },
  { value: "HUB_MANAGER", label: "Hub Manager" },
  { value: "EXECUTIVE", label: "Executive" },
  { value: "SYSTEM_ADMIN", label: "System Admin" },
];

export const STATUS_OPTIONS = [
  { value: "ACTIVE", label: "Active" },
  { value: "LOCKED", label: "Locked" },
  { value: "PENDING_VERIFICATION", label: "Pending verification" },
];

export const STATUS_TONE = {
  ACTIVE: "success",
  LOCKED: "danger",
  PENDING_VERIFICATION: "warning",
} as const;

export const ROLES_WITH_HUB = new Set(["DRIVER", "HUB_MANAGER"]);

export function roleLabel(code: string): string {
  return ROLE_OPTIONS.find((role) => role.value === code)?.label ?? code;
}

export function statusLabel(code: string): string {
  return STATUS_OPTIONS.find((status) => status.value === code)?.label ?? code;
}
