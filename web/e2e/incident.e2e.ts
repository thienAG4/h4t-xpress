// F4 + F5: a driver reports a breakdown with a photo; the hub classifies it, answers and
// keeps the parcel at the hub; the driver sees the answer.

import { expect, test } from "@playwright/test";
import { acceptNextOffer, createShopNowOrder, demoLogin, pickUpFirstParcel, setOnline, testPhoto } from "./helpers";

test("incident report, classification, answer and hold at hub", async ({ browser }) => {
  const driverContext = await browser.newContext({ viewport: { width: 420, height: 860 } });
  const driver = await driverContext.newPage();
  await demoLogin(driver, "Driver");
  await createShopNowOrder(driver);
  await setOnline(driver, true);
  await acceptNextOffer(driver);
  await setOnline(driver, false);
  const waybill = await pickUpFirstParcel(driver);

  await driver.goto("/driver/incidents/new");
  await driver.getByLabel("Select reason").selectOption("VEHICLE_BREAKDOWN");
  await driver.getByLabel("Description").fill("Engine stopped near the market, cannot continue the route.");
  await driver.locator('input[type="file"]').setInputFiles(testPhoto());
  await expect(driver.getByRole("button", { name: "Remove" })).toBeVisible();
  // Report only the parcel picked up in this test.
  for (const box of await driver.getByRole("checkbox").all()) {
    const label = await box.locator("xpath=..").innerText();
    if (!label.includes(waybill)) await box.uncheck();
  }
  await driver.getByRole("button", { name: "Confirm" }).click();
  const dialog = driver.getByRole("dialog", { name: "REPORT!" });
  await expect(dialog).toBeVisible();
  const code = (await dialog.innerText()).match(/INC-\d+/)?.[0];
  expect(code).toBeTruthy();

  const hubContext = await browser.newContext();
  const hub = await hubContext.newPage();
  await demoLogin(hub, "Hub Manager");
  await hub.goto("/hub/incidents/list?open=1");
  await hub.locator("section", { hasText: code! }).getByRole("link", { name: "Handle issue" }).click();
  await expect(hub.getByRole("heading", { name: "Vehicle breakdown" })).toBeVisible();

  await hub.getByRole("button", { name: /classification/ }).click();
  await hub.getByLabel("Manager response").fill("Bring the parcel back to the hub, we will send it tomorrow.");
  await hub.getByRole("button", { name: "Send to driver" }).click();
  await hub.getByRole("button", { name: /Hold at hub/ }).first().click();
  await hub.getByRole("button", { name: "Hold parcels at the hub" }).click();
  await expect(hub.getByRole("dialog", { name: "SUCCESS!" })).toBeVisible();
  await expect(hub.getByText("Resolved").first()).toBeVisible();

  await driver.goto("/driver/incidents");
  const card = driver.locator("section", { hasText: code! });
  await expect(card.getByText("Bring the parcel back to the hub, we will send it tomorrow.")).toBeVisible();
  await expect(card.getByText("Bring the parcels back to the hub.")).toBeVisible();

  await hub.goto(`/track/${waybill}`);
  await expect(hub.getByText(/We are sorry for the delay/).first()).toBeVisible({ timeout: 30_000 });

  await driverContext.close();
  await hubContext.close();
});
