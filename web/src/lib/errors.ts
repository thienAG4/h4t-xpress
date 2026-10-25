// Error messages - turn API error codes into short, user-facing sentences

import { ApiError } from "./http";

const MESSAGES: Record<string, string> = {
  INVALID_CREDENTIALS: "Phone/e-mail or password is incorrect.",
  ACCOUNT_LOCKED: "This account is locked. Please contact your administrator.",
  ACCOUNT_NOT_VERIFIED: "Please verify your phone number before signing in.",
  TOO_MANY_REQUESTS: "Too many attempts. Please wait a moment and try again.",
  OTP_INVALID: "The code is incorrect.",
  OTP_EXPIRED: "This code has expired. Request a new one.",
  OTP_LOCKED: "Too many wrong codes. Request a new one.",
  OTP_COOLDOWN: "Please wait before requesting a new code.",
  OTP_NOT_FOUND: "There is no active code. Request a new one.",
  OTP_NOT_AVAILABLE: "No code can be sent to this number.",
  EMAIL_TAKEN: "This e-mail is already used by another account.",
  PHONE_TAKEN: "This phone number is already used by another account.",
  HUB_REQUIRED: "Please choose a hub for this role.",
  DRIVER_FIELDS_REQUIRED: "Vehicle plate and licence number are required for drivers.",
  ROLE_CHANGE_NOT_SUPPORTED: "Switching to or from the driver role is not supported.",
  DEMO_ACCOUNT_PROTECTED: "Shared demo accounts cannot be changed. Create a new account to try this.",
  CANNOT_LOCK_SELF: "You cannot lock your own account.",
  LOCKOUT_PREVENTED: "System admins must keep user and role management.",
  WRONG_PASSWORD: "Your current password is incorrect.",
  SHIFT_FULL: "This shift is full.",
  SHIFT_OVERLAP: "This shift overlaps another shift you registered.",
  SHIFT_CLOSED: "Registration for this date is closed.",
  SHIFT_STARTED: "A shift that has started cannot be cancelled.",
  ALREADY_REGISTERED: "You are already registered for this shift.",
  NO_SHIFT_TODAY: "Register for a shift today before going online.",
  CANCEL_NOT_ALLOWED: "This order can no longer be cancelled.",
  HUB_NOT_FOUND: "Unknown hub.",
  NETWORK_ERROR: "Cannot reach the server. Check your connection and try again.",
};

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "VALIDATION_ERROR") {
      const first = Object.values(error.fieldErrors)[0];
      return first ? `Please check the form: ${first}` : "Please check the form.";
    }
    return MESSAGES[error.code] ?? error.message;
  }
  if (error instanceof TypeError) return MESSAGES.NETWORK_ERROR;
  return "Something went wrong. Please try again.";
}

export function errorCode(error: unknown): string | null {
  return error instanceof ApiError ? error.code : null;
}
