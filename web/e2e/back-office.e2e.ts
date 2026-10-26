// F8 and back office: reports with filters (E-01), route planning (H-02), settings (A-06)

import { expect, test } from "@playwright/test";
import { demoLogin } from "./helpers";

test("executive reads the report and changes the period", async ({ page }) => {
  await demoLogin(page, "Executive");
  await expect(page).toHaveURL(/\/reports$/);
  await expect(page.getByText("Total orders")).toBeVisible();
  await expect(page.getByRole("img", { name: /Orders created and Delivered/ })).toBeVisible();
  await page.getByRole("button", { name: /^Timeframe/ }).click();
  await page.getByRole("button", { name: "Last 7 days" }).click();
  await expect(page.getByRole("button", { name: "Timeframe: Last 7 days" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Download Excel" })).toBeVisible();
});

test("hub manager opens route planning with today's routes", async ({ page }) => {
  await demoLogin(page, "Hub Manager");
  await page.getByRole("link", { name: "Route planning" }).first().click();
  await expect(page.getByRole("heading", { name: "Route planning" })).toBeVisible();
  await expect(page.getByText(/stops left/).first()).toBeVisible();
});

test("system admin sees grouped settings and the audit log", async ({ page }) => {
  await demoLogin(page, "System Admin");
  await page.goto("/admin/settings");
  await expect(page.getByRole("heading", { name: "Dispatch (BR4-BR8)" })).toBeVisible();
  await page.goto("/admin/audit");
  await expect(page.getByRole("heading", { name: "Audit log" })).toBeVisible();
});
