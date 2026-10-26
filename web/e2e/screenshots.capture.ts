// README screenshots (pnpm screenshots) - run on freshly seeded demo data:
//   docker compose exec -T api python -m app.seed --reset && docker compose restart api
// Each test signs in with one demo role and saves its key screens to docs/screenshots.

import { expect, test, type Page } from "@playwright/test";
import { createShopNowOrder, demoLogin, pickUpFirstParcel, setOnline } from "./helpers";

const OUT = "../docs/screenshots";
const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };

/** Give maps and charts a moment to draw, then save the visible page without hover effects. */
async function shoot(page: Page, name: string): Promise<void> {
  await page.waitForLoadState("load");
  await page.mouse.move(0, 0);
  await page.waitForTimeout(2_500);
  await page.screenshot({ path: `${OUT}/${name}.png` });
}

/** A labelled placeholder photo drawn in the browser (the E2E one is a single pixel). */
async function evidencePhoto(page: Page): Promise<{ name: string; mimeType: string; buffer: Buffer }> {
  const dataUrl = await page.evaluate(() => {
    const canvas = Object.assign(document.createElement("canvas"), { width: 640, height: 480 });
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("No 2D canvas");
    const sky = ctx.createLinearGradient(0, 0, 0, 320);
    sky.addColorStop(0, "#8fa9c2");
    sky.addColorStop(1, "#dfe7ef");
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, 640, 320);
    ctx.fillStyle = "#5b6066";
    ctx.fillRect(0, 320, 640, 160);
    ctx.fillStyle = "#f5f5f5";
    for (let x = 20; x < 640; x += 120) ctx.fillRect(x, 396, 60, 8);
    ctx.font = "600 28px sans-serif";
    ctx.fillText("Evidence photo (demo)", 24, 52);
    return canvas.toDataURL("image/jpeg", 0.85);
  });
  return { name: "breakdown.jpg", mimeType: "image/jpeg", buffer: Buffer.from(dataUrl.split(",")[1], "base64") };
}

let waybill = "";
let incident = "";

test("driver app", async ({ browser }) => {
  const context = await browser.newContext({ viewport: PHONE, deviceScaleFactor: 2, hasTouch: true });
  const page = await context.newPage();
  await demoLogin(page, "Driver");
  await createShopNowOrder(page);
  await setOnline(page, true);
  const accept = page.getByRole("button", { name: "Accept", exact: true });
  await expect(accept).toBeVisible({ timeout: 120_000 });
  await shoot(page, "driver-offer");
  await accept.click();
  await expect(page).toHaveURL(/\/driver\/route$/);
  await setOnline(page, false);
  await page.goto("/driver/route");
  await shoot(page, "driver-route");
  waybill = await pickUpFirstParcel(page);

  // Report a breakdown on that parcel, so the hub has an incident to show.
  await page.goto("/driver/incidents/new");
  await page.getByLabel("Select reason").selectOption("VEHICLE_BREAKDOWN");
  await page.getByLabel("Description").fill("Engine stopped near the market, cannot continue the route.");
  await page.locator('input[type="file"]').setInputFiles(await evidencePhoto(page));
  for (const box of await page.getByRole("checkbox").all()) {
    const label = await box.locator("xpath=..").innerText();
    if (!label.includes(waybill)) await box.uncheck();
  }
  await shoot(page, "driver-incident");
  await page.getByRole("button", { name: "Confirm" }).click();
  const dialog = page.getByRole("dialog", { name: "REPORT!" });
  await expect(dialog).toBeVisible();
  incident = (await dialog.innerText()).match(/INC-\d+/)?.[0] ?? "";
  await context.close();
});

test("hub manager", async ({ browser }) => {
  const context = await browser.newContext({ viewport: DESKTOP });
  const page = await context.newPage();
  await demoLogin(page, "Hub Manager");
  await shoot(page, "hub-dashboard");
  await page.goto("/hub/tracking");
  // Follow the first order in "Find an order", as in the Figma tracking frame.
  await page.getByRole("button", { name: /SN\d+/ }).first().click();
  await expect(page.getByText("Shipment ID")).toBeVisible();
  await shoot(page, "hub-tracking");
  await page.goto("/hub/routes");
  await expect(page.getByText(/stops left/).first()).toBeVisible();
  await shoot(page, "hub-route-planning");
  await page.goto("/hub/incidents/list?open=1");
  await page.locator("section", { hasText: incident }).getByRole("link", { name: "Handle issue" }).click();
  await expect(page.getByRole("button", { name: /classification/ })).toBeVisible();
  await shoot(page, "hub-incident");
  await context.close();
});

test("executive", async ({ browser }) => {
  const context = await browser.newContext({ viewport: DESKTOP });
  const page = await context.newPage();
  await demoLogin(page, "Executive");
  await expect(page.getByText("Total orders")).toBeVisible();
  await shoot(page, "reports");
  await context.close();
});

test("system admin", async ({ browser }) => {
  const context = await browser.newContext({ viewport: DESKTOP });
  const page = await context.newPage();
  await demoLogin(page, "System Admin");
  await page.goto("/admin/settings");
  await expect(page.getByRole("heading", { name: "Dispatch (BR4-BR8)" })).toBeVisible();
  await shoot(page, "admin-settings");
  await context.close();
});

test("partner and customer", async ({ browser }) => {
  const context = await browser.newContext({ viewport: DESKTOP });
  const page = await context.newPage();
  await page.goto("/shopnow/demo");
  await shoot(page, "shopnow-demo");
  await page.goto(`/track/${waybill}`);
  await shoot(page, "customer-tracking");
  await page.goto("/login");
  await shoot(page, "login");
  await context.close();
});
