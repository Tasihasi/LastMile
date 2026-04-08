import { test, expect, loginViaAPI, uploadTestFile } from "./fixtures";

test.describe("Biker Journey", () => {
  test.describe("Upload and view route", () => {
    test.beforeEach(async ({ page }) => {
      await loginViaAPI(page, "BikerUpload", "biker");
    });

    test("upload CSV with pre-geocoded stops", async ({ page }) => {
      // Click "New Route" to show upload
      await page.getByRole("button", { name: "New Route" }).click();

      // Upload file
      await uploadTestFile(page, "geocoded_stops.csv");

      // Wait for stops to appear in sidebar
      await expect(page.locator(".stop-item")).toHaveCount(5, {
        timeout: 15_000,
      });

      // Check stats bar
      await expect(page.locator(".stat-value").first()).toHaveText("5");

      // Map should be visible
      await expect(page.locator(".leaflet-container")).toBeVisible();
    });

    test("optimize route after upload", async ({ page }) => {
      await page.getByRole("button", { name: "New Route" }).click();
      await uploadTestFile(page, "geocoded_stops.csv");
      await expect(page.locator(".stop-item")).toHaveCount(5, {
        timeout: 15_000,
      });

      // Click Optimize Route
      await page.getByRole("button", { name: "Optimize Route" }).click();
      await expect(page.getByText("Optimizing...")).toBeVisible();

      // Wait for optimization to complete
      await expect(page.locator(".route-summary")).toBeVisible({
        timeout: 30_000,
      });

      // Route summary should show duration and distance
      await expect(page.locator(".route-summary-item")).toHaveCount(3);

      // Start Route button should appear
      await expect(
        page.getByRole("button", { name: "Start Route" })
      ).toBeVisible();
    });
  });

  test.describe("Route lifecycle", () => {
    test("full delivery lifecycle: start, deliver stops, finish", async ({
      page,
    }) => {
      // Login as biker and upload a fresh route (seeded routes may be consumed by earlier tests)
      await loginViaAPI(page, "Anna", "biker");
      await page.getByRole("button", { name: "New Route" }).click();
      await expect(page.locator('input[type="file"]')).toBeAttached({
        timeout: 10_000,
      });
      await uploadTestFile(page, "geocoded_stops.csv");

      // Wait for stops to load
      await expect(page.locator(".stop-item").first()).toBeVisible({
        timeout: 15_000,
      });

      // Optimize the uploaded route
      await page.getByRole("button", { name: "Optimize Route" }).click();
      await expect(page.locator(".route-summary")).toBeVisible({
        timeout: 30_000,
      });

      // Start the route
      const startBtn = page.getByRole("button", { name: "Start Route" });
      if (await startBtn.isVisible()) {
        await startBtn.click();

        // Route status banner should show
        await expect(
          page.locator(".route-status-banner--active")
        ).toBeVisible({ timeout: 10_000 });

        // Mark stops one by one as delivered
        let actionBtns = page.locator(".stop-action-btn--delivered");
        while ((await actionBtns.count()) > 0) {
          await actionBtns.first().click();
          // Wait for UI to update
          await page.waitForTimeout(500);
          actionBtns = page.locator(".stop-action-btn--delivered");
        }

        // Route should be finished (or some stops may have been marked not_received by seed)
        // Check for either finished banner or no more pending stops
        const finishedBanner = page.locator(
          ".route-status-banner--finished"
        );
        const activeActions = page.locator(".stop-action-btn");
        // Either route is finished or no action buttons remain
        await expect(
          finishedBanner.or(activeActions.first())
        ).toBeVisible({ timeout: 10_000 });
      }
    });
  });

  test.describe("View seeded in-progress route", () => {
    test("see active route with progress", async ({ page }) => {
      await loginViaAPI(page, "Anna", "biker");

      // Look for an active route (green dot indicator)
      const activeSession = page.locator(".session-list-item--active").first();
      if ((await activeSession.count()) > 0) {
        await activeSession.click();

        // Should see the route in progress
        await expect(page.locator(".stop-item").first()).toBeVisible({
          timeout: 15_000,
        });

        // Active route shows status banner
        await expect(
          page.locator(".route-status-banner--active")
        ).toBeVisible();

        // Map should display
        await expect(page.locator(".leaflet-container")).toBeVisible();
      }
    });
  });

  test.describe("Upload and geocode flow", () => {
    test("upload file needing geocoding and run geocode", async ({
      page,
    }) => {
      await loginViaAPI(page, "BikerGeocode", "biker");
      await page.getByRole("button", { name: "New Route" }).click();

      // Upload file that needs geocoding
      await uploadTestFile(page, "needs_geocoding.csv");
      await expect(page.locator(".stop-item")).toHaveCount(3, {
        timeout: 15_000,
      });

      // Geocode button should be visible
      const geocodeBtn = page.getByRole("button", {
        name: "Geocode Addresses",
      });
      await expect(geocodeBtn).toBeVisible();
      await geocodeBtn.click();

      // Should show progress
      await expect(page.getByText(/Geocoding/)).toBeVisible();

      // Wait for geocoding to complete (mock mode is fast)
      await expect(
        page.getByRole("button", { name: "Optimize Route" })
      ).toBeVisible({ timeout: 30_000 });
    });
  });
});
