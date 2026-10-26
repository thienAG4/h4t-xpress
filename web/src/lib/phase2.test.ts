// Tests for Phase 2 helpers: business-time inputs, relative times, distance and labels

import { describe, expect, it } from "vitest";
import { errorMessage } from "./errors";
import { formatClock, formatKm, formatRelative, fromLocalInput, toLocalInput } from "./format";
import { distanceKm } from "./geo";
import { FAILURE_REASON, INCIDENT_TYPE, REPORTABLE_TYPES, options } from "./labels";
import { ApiError } from "./http";

describe("business time", () => {
  it("round-trips datetime-local values in Vietnam time (UTC+7)", () => {
    const instant = new Date("2026-10-25T07:30:00Z");
    expect(toLocalInput(instant)).toBe("2026-10-25T14:30");
    expect(fromLocalInput("2026-10-25T14:30")).toBe("2026-10-25T07:30:00.000Z");
    expect(formatClock("2026-10-25T07:30:00Z")).toBe("14:30");
  });

  it("describes times relative to now", () => {
    const now = new Date("2026-10-25T07:00:00Z").getTime();
    expect(formatRelative("2026-10-25T07:20:00Z", now)).toBe("in 20 min");
    expect(formatRelative("2026-10-25T06:45:00Z", now)).toBe("15 min ago");
    expect(formatRelative("2026-10-25T04:00:00Z", now)).toBe("3 h ago");
    expect(formatRelative("2026-10-21T07:00:00Z", now)).toBe("4 d ago");
    expect(formatRelative(null, now)).toBe("-");
  });
});

describe("geo", () => {
  it("measures straight-line distance in km", () => {
    // Di An hub to Ben Thanh market, about 17 km.
    const km = distanceKm({ lat: 10.906, lng: 106.77 }, { lat: 10.7725, lng: 106.698 });
    expect(km).toBeGreaterThan(16);
    expect(km).toBeLessThan(18);
    expect(formatKm(km)).toMatch(/^1\d\.\d km$/);
  });
});

describe("labels", () => {
  it("never offers system incident types to drivers", () => {
    expect(REPORTABLE_TYPES).not.toContain("ETA_ANOMALY");
    expect(REPORTABLE_TYPES).not.toContain("DRIVER_IDLE");
    expect(REPORTABLE_TYPES.every((type) => INCIDENT_TYPE[type])).toBe(true);
  });

  it("turns label maps into select options", () => {
    const reasons = options(FAILURE_REASON);
    expect(reasons).toHaveLength(5);
    expect(reasons[0]).toEqual({ value: "CUSTOMER_ABSENT", label: "Customer not at home" });
  });

  it("explains Phase 2 error codes", () => {
    expect(errorMessage(new ApiError(422, "EVIDENCE_REQUIRED", "x"))).toBe("Add at least one photo as evidence.");
    expect(errorMessage(new ApiError(409, "INCIDENT_OPEN", "x"))).toContain("open incident");
  });
});

describe("polyline", () => {
  it("decodes the reference example", async () => {
    const { decodePolyline } = await import("./polyline");
    expect(decodePolyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@")).toEqual([
      [38.5, -120.2],
      [40.7, -120.95],
      [43.252, -126.453],
    ]);
  });
});
