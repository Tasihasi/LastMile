import { test, expect, loginViaAPI, uploadTestFile } from "./fixtures";

test.describe("Settings and Theme", () => {
  test.beforeEach(async ({ page }) => {
    await loginViaAPI(page, "BikerSettings", "biker");
    await page.getByRole("button", { name: "New Route" }).click();
    await uploadTestFile(page, "geocoded_stops.csv");
    await expect(page.locator(".stop-item").first()).toBeVisible({
      timeout: 15_000,
    });
  });

  test.describe("Theme toggle", () => {
    test("toggle dark mode and back", async ({ page }) => {
      // Find theme toggle button by title
      const darkToggle = page.locator(
        '[aria-label="Switch to dark mode"]'
      );
      const lightToggle = page.locator(
        '[aria-label="Switch to light mode"]'
      );

      // Initially light mode
      if (await darkToggle.isVisible()) {
        await darkToggle.click();
        // Should now be dark mode
        await expect(lightToggle).toBeVisible();

        // Toggle back
        await lightToggle.click();
        await expect(darkToggle).toBeVisible();
      }
    });

    test("theme persists after reload", async ({ page }) => {
      const darkToggle = page.locator(
        '[aria-label="Switch to dark mode"]'
      );
      if (await darkToggle.isVisible()) {
        await darkToggle.click();
        await page.reload();
        // After reload, should still be in dark mode
        await expect(page.locator(".stop-item").first()).toBeVisible({
          timeout: 15_000,
        });
        await expect(
          page.locator('[aria-label="Switch to light mode"]')
        ).toBeVisible();
        // Reset
        await page
          .locator('[aria-label="Switch to light mode"]')
          .click();
      }
    });
  });

  test.describe("Settings panel", () => {
    test("open and close settings panel", async ({ page }) => {
      // Click settings gear button
      const settingsBtn = page.locator('[aria-label="Route settings"]');
      await expect(settingsBtn).toBeVisible();
      await settingsBtn.click();

      // Settings panel should be visible
      await expect(page.getByText("Route Settings")).toBeVisible();

      // Close the panel
      await page.locator(".stop-detail-close").first().click();
      await expect(page.getByText("Route Settings")).not.toBeVisible();
    });

    test("change start time", async ({ page }) => {
      await page.locator('[aria-label="Route settings"]').click();
      await expect(page.getByText("Route Settings")).toBeVisible();

      const timeInput = page.locator('input[type="time"]');
      await expect(timeInput).toBeVisible();
      await timeInput.fill("09:30");

      // Value should be updated
      await expect(timeInput).toHaveValue("09:30");
    });

    test("change dwell time slider", async ({ page }) => {
      await page.locator('[aria-label="Route settings"]').click();
      await expect(page.getByText("Route Settings")).toBeVisible();

      // Dwell time slider
      const dwellSlider = page.locator('input[type="range"]').first();
      await expect(dwellSlider).toBeVisible();

      // Set to 5 minutes
      await dwellSlider.fill("5");
      await expect(dwellSlider).toHaveValue("5");
    });

    test("speed preset buttons work", async ({ page }) => {
      await page.locator('[aria-label="Route settings"]').click();

      // Click Bike preset
      const bikePreset = page.locator(".speed-preset", {
        hasText: "Bike",
      });
      if (await bikePreset.isVisible()) {
        await bikePreset.click();
        await expect(bikePreset).toHaveClass(/speed-preset--active/);
      }

      // Click Car preset
      const carPreset = page.locator(".speed-preset", {
        hasText: "Car",
      });
      if (await carPreset.isVisible()) {
        await carPreset.click();
        await expect(carPreset).toHaveClass(/speed-preset--active/);
      }
    });
  });
});
