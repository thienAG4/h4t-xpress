// E2E helpers - demo sign-in, driver availability, waiting for an offer, a test photo

import { expect, type Page } from "@playwright/test";

export type DemoRole = "Driver" | "Hub Manager" | "Executive" | "System Admin";

/** One-click demo sign-in (the login page shows these buttons in demo mode). */
export async function demoLogin(page: Page, role: DemoRole): Promise<void> {
  await page.goto("/login");
  await page.getByRole("button", { name: role, exact: true }).click();
  await expect(page).not.toHaveURL(/\/login$/);
}

export async function setOnline(page: Page, online: boolean): Promise<void> {
  await page.goto("/driver");
  const toggle = page.getByRole("switch", { name: "Ready for orders" });
  await expect(toggle).toBeVisible();
  if ((await toggle.getAttribute("aria-checked")) !== String(online)) {
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-checked", String(online));
  }
}

/** Ask ShopNow for a fresh order so dispatch always has something to offer. */
export async function createShopNowOrder(page: Page): Promise<void> {
  const response = await page.request.post("/api/v1/sim/shopnow/orders/random", {
    data: { hub_code: "DIAN", count: 1, express_ratio: 0 },
  });
  expect(response.ok()).toBeTruthy();
}

/** Wait for the offer popup (dispatch retries every minute in the demo) and accept it. */
export async function acceptNextOffer(page: Page): Promise<void> {
  const accept = page.getByRole("button", { name: "Accept", exact: true });
  await expect(accept).toBeVisible({ timeout: 120_000 });
  await accept.click();
  await expect(page).toHaveURL(/\/driver\/route$/);
}

/** A small PNG made in memory, used as proof of delivery or incident evidence. */
export function testPhoto(): { name: string; mimeType: string; buffer: Buffer } {
  const png =
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==";
  return { name: "evidence.png", mimeType: "image/png", buffer: Buffer.from(png, "base64") };
}

/**
 * Collect the first parcel on the route: scan it and start the delivery.
 * Returns its waybill code.
 */
export async function pickUpFirstParcel(page: Page): Promise<string> {
  await page.goto("/driver/route");
  const card = page.locator("section", { hasText: "To pick up" });
  const waybill = (await card.locator("p.font-semibold").first().innerText()).trim();
  await card.getByRole("button", { name: "Scan" }).first().click();
  await page.getByLabel("Waybill code").fill(waybill);
  await page.getByRole("button", { name: "Confirm" }).click();
  await page.getByRole("button", { name: /Start delivery/ }).click();
  await expect(page.getByText(/out for delivery/)).toBeVisible();
  return waybill;
}
