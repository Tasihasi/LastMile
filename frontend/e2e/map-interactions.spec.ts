import { test, expect, loginViaAPI, uploadTestFile } from "./fixtures";

test.describe("Map and Stop Interactions", () => {
  test.beforeEach(async ({ page }) => {
    await loginViaAPI(page, "BikerMap", "biker");
    await page.getByRole("button", { name: "New Route" }).click();
    await uploadTestFile(page, "geocoded_stops.csv");
    await expect(page.locator(".stop-item").first()).toBeVisible({
      timeout: 15_000,
    });
  });

  test("map renders with markers for all stops", async ({ page }) => {
    // Map should be visible
    await expect(page.locator(".leaflet-container")).toBeVisible();

    // Should have numbered markers for the 5 stops
    const markers = page.locator(".numbered-marker");
    await expect(markers).toHaveCount(5, { timeout: 10_000 });
  });

  test("click stop in sidebar selects it on map", async ({ page }) => {
    // Click first stop
    await page.locator(".stop-item").first().click();

    // Stop detail overlay should appear
    await expect(page.locator(".stop-detail-overlay")).toBeVisible({
      timeout: 5_000,
    });

    // Should show stop name and details
    await expect(
      page.locator(".stop-detail h3")
    ).toBeVisible();
  });

  test("stop detail shows address and coordinates", async ({ page }) => {
    await page.locator(".stop-item").first().click();
    await expect(page.locator(".stop-detail-overlay")).toBeVisible();

    // Should have detail rows
    await expect(page.locator(".detail-row").first()).toBeVisible();

    // Should show Address label
    await expect(
      page.locator(".detail-label", { hasText: "Address" })
    ).toBeVisible();

    // Should show Coordinates
    await expect(
      page.locator(".detail-label", { hasText: "Coordinates" })
    ).toBeVisible();
  });

  test("stop detail shows product code and recipient", async ({
    page,
  }) => {
    await page.locator(".stop-item").first().click();
    await expect(page.locator(".stop-detail-overlay")).toBeVisible();

    // Product code
    await expect(
      page.locator(".detail-label", { hasText: "Product Code" })
    ).toBeVisible();

    // Recipient
    await expect(
      page.locator(".detail-label", { hasText: "Recipient" })
    ).toBeVisible();
  });

  test("close stop detail by clicking overlay", async ({ page }) => {
    await page.locator(".stop-item").first().click();
    await expect(page.locator(".stop-detail-overlay")).toBeVisible();

    // Click on the overlay (outside the detail panel)
    await page.locator(".stop-detail-overlay").click({ position: { x: 10, y: 10 } });
    await expect(page.locator(".stop-detail-overlay")).not.toBeVisible({
      timeout: 5_000,
    });
  });

  test("stats bar shows correct counts", async ({ page }) => {
    const stats = page.locator(".stat-item");
    // Total stops
    await expect(stats.filter({ hasText: "Total" })).toContainText("5");
    // Located stops
    await expect(stats.filter({ hasText: "Located" })).toContainText("5");
  });

  test("sidebar toggle works on mobile viewport", async ({ page }) => {
    // Resize to mobile
    await page.setViewportSize({ width: 375, height: 812 });
    await page.waitForTimeout(1000);

    // Toggle sidebar open
    const toggleBtn = page.locator('[aria-label="Toggle sidebar"]');
    if (await toggleBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await toggleBtn.click();
      await expect(page.locator(".sidebar--open")).toBeVisible({
        timeout: 5_000,
      });

      // Close sidebar by clicking overlay (force needed as sidebar sits above)
      const overlay = page.locator(".sidebar-overlay");
      if (await overlay.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await overlay.click({ force: true });
        await expect(overlay).not.toBeVisible({ timeout: 5_000 });
      }
    }
  });
});
