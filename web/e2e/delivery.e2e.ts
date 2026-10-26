// F3: a driver accepts an offer, scans the parcel, delivers with a photo; the customer
// sees "Delivered" on the ShopNow tracking page.

import { expect, test } from "@playwright/test";
import { acceptNextOffer, createShopNowOrder, demoLogin, pickUpFirstParcel, setOnline, testPhoto } from "./helpers";

test("offer, scan, deliver with proof, customer tracking", async ({ page }) => {
  await demoLogin(page, "Driver");
  await createShopNowOrder(page);
  await setOnline(page, true);
  await acceptNextOffer(page);
  // Going offline stops further offers from covering the screen during the flow.
  await setOnline(page, false);

  const waybill = await pickUpFirstParcel(page);
  await page.getByRole("link", { name: new RegExp(waybill) }).click();
  await page.getByRole("link", { name: "Deliver" }).first().click();

  await page.locator('input[type="file"]').setInputFiles(testPhoto());
  await expect(page.getByRole("button", { name: "Remove" })).toBeVisible();
  await page.getByRole("button", { name: "Successful" }).click();
  await expect(page.getByRole("heading", { name: "Successful" })).toBeVisible();

  // The webhook reaches ShopNow within a few seconds (worker loop).
  await expect(async () => {
    await page.goto(`/track/${waybill}`);
    await expect(page.getByRole("heading", { name: "Delivered" })).toBeVisible({ timeout: 2_000 });
  }).toPass({ timeout: 45_000 });
});
