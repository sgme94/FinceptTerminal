import { expect, test } from "@playwright/test";

const routes = [
  ["F1", "Overview"],
  ["F2", "Markets"],
  ["F3", "Signals"],
  ["F4", "Risk"],
  ["F5", "News"],
  ["F6", "Data"],
  ["F7", "Agents"],
  ["F8", "Audit"]
] as const;

test.describe("Polymarket terminal visual shell", () => {
  test("desktop 1700x900 loads shell with right rail and no horizontal overflow", async ({ page }) => {
    await page.setViewportSize({ width: 1700, height: 900 });
    const statusResponse = page.waitForResponse("http://127.0.0.1:8765/api/bot/status");
    const positionsResponse = page.waitForResponse("http://127.0.0.1:8765/api/positions?deployment_id=default");
    const tradesResponse = page.waitForResponse("http://127.0.0.1:8765/api/trades?deployment_id=default");
    await page.goto("/");
    expect((await statusResponse).ok()).toBe(true);
    expect((await positionsResponse).ok()).toBe(true);
    expect((await tradesResponse).ok()).toBe(true);

    await expect(page.getByLabel("Polymarket terminal")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
    await expect(page.getByText("mock fallback")).toBeHidden();
    const contextRail = page.getByLabel("Context rail");
    await expect(contextRail).toBeVisible();
    await expect(contextRail.getByRole("heading", { name: "Live News", exact: true })).toBeVisible();

    const hasOverflow = await page.evaluate(() => {
      const root = document.documentElement;
      return root.scrollWidth > root.clientWidth || document.body.scrollWidth > window.innerWidth;
    });
    expect(hasOverflow).toBe(false);
  });

  test("mobile 390x844 loads drawer, collapses right rail, and has no horizontal overflow", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");

    await expect(page.getByRole("button", { name: "Open menu" })).toBeVisible();
    await page.getByRole("button", { name: "Open menu" }).click();
    await expect(page.getByLabel("Mobile route drawer")).toBeVisible();
    await expect(page.getByRole("button", { name: "Risk drawer" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Audit drawer" })).toBeVisible();
    await expect(page.getByLabel("Context rail")).toBeHidden();

    const hasOverflow = await page.evaluate(() => {
      const root = document.documentElement;
      return root.scrollWidth > root.clientWidth || document.body.scrollWidth > window.innerWidth;
    });
    expect(hasOverflow).toBe(false);
  });

  test("F1-F8 keyboard shortcuts switch full route page titles", async ({ page }) => {
    await page.setViewportSize({ width: 1700, height: 900 });
    await page.goto("/");

    for (const [key, title] of routes) {
      await page.keyboard.press(key);
      await expect(page.getByRole("heading", { name: title, exact: true })).toBeVisible();
    }
  });
});
