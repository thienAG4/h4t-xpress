// Auth API - sign-in, sign-up with OTP, session and password recovery calls

import { request } from "@/lib/http";
import { useSession } from "@/lib/session";
import type { Hub, Me, OtpSent, RegisterDriverInput, RoleCode, TokenResponse } from "@/types";

function startSession(response: TokenResponse): TokenResponse {
  useSession.getState().setSession(response.access_token, response.user);
  return response;
}

/**
 * Sign in with e-mail or phone number (FR-A-03).
 */
export async function login(identifier: string, password: string): Promise<TokenResponse> {
  const response = await request<TokenResponse>("/auth/login", {
    method: "POST",
    body: { identifier, password },
    auth: false,
  });
  return startSession(response);
}

/**
 * One-click sign-in as the demo account of a role (demo deployments only).
 */
export async function demoLogin(role: RoleCode): Promise<TokenResponse> {
  const response = await request<TokenResponse>("/auth/demo-login", {
    method: "POST",
    body: { role },
    auth: false,
  });
  return startSession(response);
}

export async function logout(): Promise<void> {
  try {
    await request<void>("/auth/logout", { method: "POST", auth: false });
  } finally {
    useSession.getState().clear();
  }
}

export function registerDriver(data: RegisterDriverInput): Promise<OtpSent> {
  return request<OtpSent>("/auth/register/driver", { method: "POST", body: data, auth: false });
}

export async function verifyOtp(phone: string, code: string): Promise<TokenResponse> {
  const response = await request<TokenResponse>("/auth/otp/verify", {
    method: "POST",
    body: { phone, code },
    auth: false,
  });
  return startSession(response);
}

export function resendOtp(phone: string): Promise<OtpSent> {
  return request<OtpSent>("/auth/otp/resend", {
    method: "POST",
    body: { phone, purpose: "REGISTER" },
    auth: false,
  });
}

export type ForgotPasswordResult = { sent: boolean; phone_hint: string | null; demo_code: string | null };

export function forgotPassword(identifier: string): Promise<ForgotPasswordResult> {
  return request<ForgotPasswordResult>("/auth/password/forgot", {
    method: "POST",
    body: { identifier },
    auth: false,
  });
}

export function resetPassword(identifier: string, code: string, newPassword: string): Promise<void> {
  return request<void>("/auth/password/reset", {
    method: "POST",
    body: { identifier, code, new_password: newPassword },
    auth: false,
  });
}

export function fetchMe(): Promise<Me> {
  return request<Me>("/me");
}

export function updateMe(data: { full_name?: string; phone?: string; address?: string }): Promise<Me> {
  return request<Me>("/me", { method: "PATCH", body: data });
}

export function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  return request<void>("/me/password", {
    method: "POST",
    body: { current_password: currentPassword, new_password: newPassword },
  });
}

export function listHubs(): Promise<Hub[]> {
  return request<Hub[]>("/hubs", { auth: false });
}
