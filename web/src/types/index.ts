// Shared API types - short aliases over the schema generated from the backend OpenAPI

import type { components } from "./api";

type Schemas = components["schemas"];

export type Me = Schemas["MeOut"];
export type User = Schemas["UserOut"];
export type UserCreateInput = Schemas["UserCreateIn"];
export type UserUpdateInput = Schemas["UserUpdateIn"];
export type Hub = Schemas["HubOut"];
export type Role = Schemas["RoleOut"];
export type Permission = Schemas["PermissionOut"];
export type TokenResponse = Schemas["TokenOut"];
export type OtpSent = Schemas["OtpSentOut"];
export type RegisterDriverInput = Schemas["RegisterDriverIn"];
export type DriverToday = Schemas["DriverTodayOut"];
export type ShiftDay = Schemas["ShiftDayOut"];
export type ShiftSlot = Schemas["ShiftSlotOut"];
export type Registration = Schemas["RegistrationOut"];
export type SimOrder = Schemas["SimOrderOut"];
export type SimWebhook = Schemas["SimWebhookOut"];
export type ManualOrderInput = Schemas["ManualOrderIn"];
export type RoleCode = Schemas["RoleCode"];

export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};
