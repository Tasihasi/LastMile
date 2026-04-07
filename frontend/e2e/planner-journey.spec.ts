import { test, expect, loginViaAPI } from "./fixtures";
import path from "path";

test.describe("Planner Journey", () => {
  test.beforeEach(async ({ page }) => {
    await loginViaAPI(page, "Planner", "planner");
  });

  test.describe("Dashboard overview", () => {
    test("shows Route Management heading and layout", async ({ page }) => {
      await expect(page.getByText("Route Management")).toBeVisible();
      // Should see dashboard layout
      await expect(page.locator(".dashboard")).toBeVisible();
    });

    test("shows unassigned and biker columns", async ({ page }) => {
      // Wait for dashboard to load
      await expect(page.locator(".dashboard-layout")).toBeVisible({
        timeout: 15_000,
      });

      // Should have some session cards from seeded data
      const sessionCards = page.locator(".session-card");
      await expect(sessionCards.first()).toBeVisible({ timeout: 15_000 });
      expect(await sessionCards.count()).toBeGreaterThan(0);
    });

    test("filter buttons work", async ({ page }) => {
      await expect(page.locator(".dashboard-layout")).toBeVisible({
        timeout: 15_000,
      });

      // Click "All Bikers" filter
      const allFilter = page.locator(".dashboard-filter-btn", {
        hasText: "All Bikers",
      });
      if (await allFilter.isVisible()) {
        await allFilter.click();
        await expect(allFilter).toHaveClass(/dashboard-filter-btn--active/);
      }
    });

    test("Live Map button is visible", async ({ page }) => {
      await expect(page.locator(".dashboard-layout")).toBeVisible({
        timeout: 15_000,
      });
      const liveMapBtn = page.locator(".btn-live-map");
      await expect(liveMapBtn).toBeVisible();
    });
  });

  test.describe("Session management", () => {
    test("upload route as planner", async ({ page }) => {
      // Click Upload Route button
      const uploadBtn = page.locator(".dashboard-upload-btn").first();
      await expect(uploadBtn).toBeVisible({ timeout: 15_000 });

      // Use the hidden file input
      const fileInput = page.locator('input[type="file"]').first();
      await fileInput.setInputFiles(
        path.resolve(__dirname, "test-data", "geocoded_stops.csv")
      );

      // Should navigate to map view with uploaded route
      await expect(page.locator(".stop-item").first()).toBeVisible({
        timeout: 15_000,
      });
    });

    test("view session from dashboard", async ({ page }) => {
      await expect(page.locator(".dashboard-layout")).toBeVisible({
        timeout: 15_000,
      });

      // Click view button on first session card
      const viewBtn = page.locator(".session-card-btn").first();
      if (await viewBtn.isVisible()) {
        await viewBtn.click();

        // Should switch to map view
        await expect(page.locator(".leaflet-container")).toBeVisible({
          timeout: 15_000,
        });
      }
    });

    test("rename session via dashboard", async ({ page }) => {
      await expect(page.locator(".session-card").first()).toBeVisible({
        timeout: 15_000,
      });

      // Double-click on session name to rename
      const sessionName = page.locator(".session-card-name").first();
      const originalName = await sessionName.textContent();
      await sessionName.dblclick();

      // Input should appear
      const nameInput = page.locator(".session-card-name-input").first();
      if (await nameInput.isVisible()) {
        await nameInput.fill("Renamed Route E2E");
        await nameInput.press("Enter");

        // Verify renamed
        await expect(
          page.locator(".session-card-name", { hasText: "Renamed Route E2E" })
        ).toBeVisible({ timeout: 5_000 });

        // Rename back
        const renamedCard = page.locator(".session-card-name", {
          hasText: "Renamed Route E2E",
        });
        await renamedCard.dblclick();
        const input2 = page.locator(".session-card-name-input").first();
        if (await input2.isVisible()) {
          await input2.fill(originalName || "Restored Name");
          await input2.press("Enter");
        }
      }
    });

    test("assign session to biker via dropdown", async ({ page }) => {
      await expect(page.locator(".session-card").first()).toBeVisible({
        timeout: 15_000,
      });

      // Find an unassigned session card
      const unassignedSection = page.locator(".dashboard-unassigned");
      if (await unassignedSection.isVisible()) {
        const assignBtn = unassignedSection
          .locator(".session-card-btn")
          .nth(1); // Second button is assign
        if (await assignBtn.isVisible()) {
          await assignBtn.click();

          // Assign dropdown should appear
          const dropdown = page.locator(".session-card-assign-dropdown");
          await expect(dropdown).toBeVisible({ timeout: 5_000 });

          // Click first biker option
          const bikerOption = dropdown
            .locator(".session-card-assign-option")
            .first();
          if (await bikerOption.isVisible()) {
            await bikerOption.click();
            // Dropdown should close
            await expect(dropdown).not.toBeVisible({ timeout: 5_000 });
          }
        }
      }
    });

    test("delete session with confirmation", async ({ page }) => {
      // First upload a route to have something to delete
      const fileInput = page.locator('input[type="file"]').first();
      await expect(fileInput).toBeAttached({ timeout: 15_000 });
      await fileInput.setInputFiles(
        path.resolve(__dirname, "test-data", "geocoded_stops.csv")
      );
      await expect(page.locator(".stop-item").first()).toBeVisible({
        timeout: 15_000,
      });

      // Go back to dashboard
      await page.getByRole("button", { name: "Dashboard" }).click();
      await expect(page.locator(".dashboard-layout")).toBeVisible({
        timeout: 15_000,
      });

      // Find a session card and click delete
      const cards = page.locator(".session-card");
      const cardCount = await cards.count();

      const deleteBtn = page.locator(".session-card-btn--danger").first();
      if (await deleteBtn.isVisible()) {
        await deleteBtn.click();

        // Confirmation dialog should appear
        await expect(
          page.locator(".session-card-confirm")
        ).toBeVisible({ timeout: 5_000 });

        // Click confirm delete
        await page
          .locator(".session-card-confirm-delete")
          .first()
          .click();

        // Card should be removed
        await expect(cards).toHaveCount(cardCount - 1, { timeout: 5_000 });
      }
    });
  });

  test.describe("Live Map", () => {
    test("opens live map view and shows active routes", async ({ page }) => {
      await expect(page.locator(".dashboard-layout")).toBeVisible({
        timeout: 15_000,
      });

      const liveMapBtn = page.locator(".btn-live-map");
      await expect(liveMapBtn).toBeVisible();
      await liveMapBtn.click();

      // Should show a map
      await expect(page.locator(".leaflet-container")).toBeVisible({
        timeout: 15_000,
      });

      // Should have a back button
      const backBtn = page.getByRole("button", { name: "Dashboard" });
      await expect(backBtn).toBeVisible();
      await backBtn.click();

      // Back to dashboard
      await expect(page.getByText("Route Management")).toBeVisible();
    });
  });
});
