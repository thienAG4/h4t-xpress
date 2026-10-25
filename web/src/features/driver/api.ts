// Driver API - home summary, shift slots, registrations and availability

import { request } from "@/lib/http";
import type { DriverToday, Registration, ShiftDay } from "@/types";

export function fetchToday(): Promise<DriverToday> {
  return request<DriverToday>("/driver/today");
}

export function fetchShiftDays(days = 7): Promise<ShiftDay[]> {
  return request<ShiftDay[]>("/driver/shifts", { query: { days } });
}

export function registerShift(shiftId: string, workDate: string): Promise<Registration> {
  return request<Registration>("/driver/shift-registrations", {
    method: "POST",
    body: { shift_id: shiftId, work_date: workDate },
  });
}

export function cancelRegistration(registrationId: string): Promise<void> {
  return request<void>(`/driver/shift-registrations/${registrationId}`, { method: "DELETE" });
}

export function setAvailability(online: boolean): Promise<{ availability: "ONLINE" | "OFFLINE" }> {
  return request("/driver/availability", { method: "PUT", body: { online } });
}
