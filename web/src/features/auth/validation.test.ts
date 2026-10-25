// Tests for sign-up validation rules (must match the API rules in core/validators.py)

import { describe, expect, it } from "vitest";
import { isValidPhone, normalizePhone, passwordProblem, validateSignUp, type SignUpForm } from "./validation";

describe("phone numbers", () => {
  it("accepts local and +84 formats and normalises them", () => {
    expect(normalizePhone("+84 912 345 678")).toBe("0912345678");
    expect(normalizePhone("84912345678")).toBe("0912345678");
    expect(isValidPhone("0912.345.678")).toBe(true);
  });

  it("rejects numbers with the wrong length", () => {
    expect(isValidPhone("091234567")).toBe(false);
    expect(isValidPhone("12345")).toBe(false);
  });
});

describe("password policy", () => {
  it("requires length, letter, number and special character", () => {
    expect(passwordProblem("short")).toBe("At least 8 characters");
    expect(passwordProblem("abcdefgh")).toBe("Must include a letter and a number");
    expect(passwordProblem("abcd1234")).toBe("Must include a special character");
    expect(passwordProblem("Secret#123")).toBeNull();
  });
});

describe("sign-up form", () => {
  const valid: SignUpForm = {
    full_name: "Nguyen Van A",
    phone: "0912345678",
    email: "a@example.com",
    password: "Secret#123",
    confirm_password: "Secret#123",
    hub_id: "hub-1",
    vehicle_plate: "59X1-123.45",
    license_no: "790123456789",
  };

  it("has no errors for a complete form", () => {
    expect(validateSignUp(valid)).toEqual({});
  });

  it("reports each invalid field", () => {
    const errors = validateSignUp({ ...valid, confirm_password: "other", hub_id: "", email: "bad" });
    expect(Object.keys(errors).sort()).toEqual(["confirm_password", "email", "hub_id"]);
  });
});
