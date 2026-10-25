// Tests for shared helpers: formatting, role home pages and API error mapping

import { describe, expect, it } from "vitest";
import type { Me } from "@/types";
import { errorMessage } from "./errors";
import { formatDay, formatPhone, formatTime } from "./format";
import { ApiError } from "./http";
import { hasPermission, homePathFor } from "./session";

describe("format", () => {
  it("formats dates, times and phone numbers", () => {
    expect(formatDay("2026-10-26")).toBe("Mon, 26 Oct");
    expect(formatTime("07:00:00")).toBe("07:00");
    expect(formatPhone("0120000001")).toBe("0120 000 001");
    expect(formatPhone(null)).toBe("-");
  });
});

describe("session helpers", () => {
  const user = (role: string, permissions: string[] = []) => ({ role, permissions }) as unknown as Me;

  it("sends each role to its own home page", () => {
    expect(homePathFor(user("DRIVER"))).toBe("/driver");
    expect(homePathFor(user("HUB_MANAGER"))).toBe("/hub");
    expect(homePathFor(user("EXECUTIVE"))).toBe("/reports");
    expect(homePathFor(user("SYSTEM_ADMIN"))).toBe("/admin");
    expect(homePathFor(null)).toBe("/");
  });

  it("checks permission codes", () => {
    expect(hasPermission(user("DRIVER", ["shift.register"]), "shift.register")).toBe(true);
    expect(hasPermission(user("DRIVER", ["shift.register"]), "user.manage")).toBe(false);
    expect(hasPermission(null, "user.manage")).toBe(false);
  });
});

describe("API errors", () => {
  it("maps known codes to friendly messages", () => {
    const error = new ApiError(409, "SHIFT_FULL", "This shift is full");
    expect(errorMessage(error)).toBe("This shift is full.");
  });

  it("exposes field errors of validation responses", () => {
    const error = new ApiError(422, "VALIDATION_ERROR", "Request data is invalid", [
      { field: "phone", message: "Phone number must have 10 digits" },
    ]);
    expect(error.fieldErrors).toEqual({ phone: "Phone number must have 10 digits" });
    expect(errorMessage(error)).toContain("Phone number must have 10 digits");
  });

  it("falls back to the server message for unknown codes", () => {
    expect(errorMessage(new ApiError(400, "SOMETHING_NEW", "Server says no"))).toBe("Server says no");
  });
});
