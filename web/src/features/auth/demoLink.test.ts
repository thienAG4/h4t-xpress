// Tests for the /demo/:role deep link slugs

import { describe, expect, it } from "vitest";
import { demoRoleFromSlug } from "./demoLink";

describe("demo deep link", () => {
  it("maps each short name to its role code, ignoring case", () => {
    expect(demoRoleFromSlug("driver")).toBe("DRIVER");
    expect(demoRoleFromSlug("Hub")).toBe("HUB_MANAGER");
    expect(demoRoleFromSlug("executive")).toBe("EXECUTIVE");
    expect(demoRoleFromSlug("ADMIN")).toBe("SYSTEM_ADMIN");
  });

  it("returns null for unknown or missing slugs", () => {
    expect(demoRoleFromSlug("customer")).toBeNull();
    expect(demoRoleFromSlug(undefined)).toBeNull();
  });
});
