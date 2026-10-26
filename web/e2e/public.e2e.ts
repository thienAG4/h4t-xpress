// Public pages and route guards

import { expect, test } from "@playwright/test";
import { demoLogin } from "./helpers";

test("landing page and customer tracking for an unknown waybill", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Last-mile delivery/ })).toBeVisible();

  await page.goto("/track/NOPE0000");
  await expect(page.getByText("We could not find this waybill")).toBeVisible();
});

test("a driver cannot open the hub screens", async ({ page }) => {
  await demoLogin(page, "Driver");
  await page.goto("/hub");
  await expect(page).toHaveURL(/\/driver$/);
});
