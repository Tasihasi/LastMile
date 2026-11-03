import { test, expect, loginViaAPI, API_BASE } from "./fixtures";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** Ensure at least one in_progress session exists for the Live Map button. */
async function ensureActiveRoute(page: import("@playwright/test").Page) {
  const token = await page.evaluate(() => localStorage.getItem("auth-token"));
  const headers = { Authorization: `Token ${token}` };

  // Check if there's already an active route
  const res = await page.request.get(`${API_BASE}/sessions/`, { headers });
  const sessions = await res.json();
  if (sessions.some((s: { status: string }) => s.status === "in_progress")) {
    return;
  }

  // Try starting an existing not_started, pre-optimized route
  const notStarted = sessions.find(
    (s: { status: string; owner_name: string | null }) =>
      s.status === "not_started" && s.owner_name != null
  );
  if (notStarted) {
    const startRes = await page.request.patch(
      `${API_BASE}/sessions/${notStarted.id}/start/`,
      { headers }
    );
    if (startRes.ok()) return;
  }

  // No suitable route exists — upload a small geocoded CSV, optimize, start
  const fs = await import("fs");
  const csvPath = path.resolve(__dirname, "test-data", "geocoded_stops.csv");
  const csvContent = fs.readFileSync(csvPath);
  const uploadRes = await page.request.post(`${API_BASE}/upload/`, {
    headers,
    multipart: {
      file: { name: "active_route.csv", mimeType: "text/csv", buffer: csvContent },
    },
  });
  const { id: sessionId } = await uploadRes.json();

  await page.request.post(`${API_BASE}/sessions/${sessionId}/optimize/`, {
    headers,
  });
  await page.request.patch(`${API_BASE}/sessions/${sessionId}/start/`, {
    headers,
  });
}

test.describe("Planner Journey", () => {
  test.beforeEach(async ({ page }) => {
    await loginViaAPI(page, "Planner", "planner");
  });

  test.describe("Dashboard overview", () => {
    test("shows Route Management heading and layout", async ({ page }) => {
      await expect(page.getByText("Route Management")).toBeVisible({
        timeout: 15_000,
      });
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
      // Ensure at least one in_progress route exists so the button renders
      await ensureActiveRoute(page);
      await page.reload();
      await expect(page.locator(".dashboard-layout")).toBeVisible({
        timeout: 15_000,
      });
      const liveMapBtn = page.locator(".btn-live-map");
      await expect(liveMapBtn).toBeVisible({ timeout: 10_000 });
    });
  });

  test.describe("Session management", () => {
    test("Upload Route opens the wizard; finishing it adds a card to the dashboard", async ({
      page,
    }) => {
      await expect(page.locator(".dashboard-layout")).toBeVisible({
        timeout: 15_000,
      });
      const cardsBefore = await page.locator(".session-card").count();

      await page.getByRole("button", { name: "Upload Route" }).click();
      await expect(page.locator(".wizard-stepper")).toBeVisible();

      await page
        .locator('input[type="file"]')
        .setInputFiles(path.resolve(__dirname, "test-data", "ups_terkep_teszt.xlsx"));
      await page.getByRole("button", { name: /Upload & continue/ }).click();

      const footer = page.locator(".wizard-footer");
      const toFix = footer.getByRole("button", { name: /(Fix|Review) addresses/ });
      await expect(toFix).toBeEnabled({ timeout: 90_000 });
      await toFix.click();
      await footer.getByRole("button", { name: /^Continue/ }).click();
      await expect(page.getByText(/\d+ of 14 stops included/)).toBeVisible();

      // Only after the zip codes are settled does the biker distribution come.
      await footer.getByRole("button", { name: /^Continue/ }).click();
      await expect(page.getByRole("dialog", { name: "Split route planner" })).toBeVisible();
      await expect(page.getByRole("button", { name: /^Split / })).toBeVisible();

      // Back to the dashboard: the uploaded route is there as a new card.
      await page.getByRole("button", { name: "Dashboard" }).click();
      await expect(page.locator(".session-card")).toHaveCount(cardsBefore + 1, {
        timeout: 15_000,
      });
    });

    test("rejected upload surfaces an error in the wizard (no silent failure)", async ({
      page,
    }) => {
      await expect(page.locator(".dashboard-layout")).toBeVisible({
        timeout: 15_000,
      });

      await page.getByRole("button", { name: "Upload Route" }).click();
      // Unsupported format -> backend 400; the wizard must report it.
      await page.locator('input[type="file"]').setInputFiles({
        name: "bad.json",
        mimeType: "application/json",
        buffer: Buffer.from('{"not":"a stop list"}'),
      });
      await page.getByRole("button", { name: /Upload & continue/ }).click();

      await expect(page.locator(".wizard-error")).toBeVisible({
        timeout: 15_000,
      });
    });

    test("view session from dashboard", async ({ page }) => {
      await expect(page.locator(".dashboard-layout")).toBeVisible({
        timeout: 15_000,
      });

      // Click view button (eye icon) on first session card
      const viewBtn = page.locator('[title="View route on map"]').first();
      if (await viewBtn.isVisible()) {
        await viewBtn.click();

        // Unplanned routes reopen in the wizard, planned ones on the map
        await expect(
          page.locator(".wizard-stepper, .leaflet-container").first()
        ).toBeVisible({ timeout: 15_000 });
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
          .locator('[title="Assign to biker"]')
          .first();
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

    test("delete session by holding the delete button", async ({ page }) => {
      // Wait for dashboard to fully load
      await expect(page.locator(".dashboard-layout")).toBeVisible({
        timeout: 20_000,
      });
      await page.waitForLoadState("networkidle");

      const cards = page.locator(".session-card");
      await expect(cards.first()).toBeVisible({ timeout: 15_000 });
      const cardCount = await cards.count();

      const deleteBtn = page.locator(".session-card-btn--danger").first();
      if (await deleteBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
        const box = (await deleteBtn.boundingBox())!;
        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);

        // A short press does nothing...
        await page.mouse.down();
        await expect(deleteBtn).toHaveClass(/hold-btn--holding/);
        await page.mouse.up();
        await expect(deleteBtn).not.toHaveClass(/hold-btn--holding/);
        await expect(cards).toHaveCount(cardCount);

        // ...holding it for the full duration deletes the route.
        await page.mouse.down();
        await expect(cards).toHaveCount(cardCount - 1, { timeout: 10_000 });
        await page.mouse.up();
      }
    });
  });

  test.describe("Live Map", () => {
    test("opens live map view and shows active routes", async ({ page }) => {
      await expect(page.locator(".dashboard-layout")).toBeVisible({
        timeout: 15_000,
      });

      // Ensure at least one in_progress route exists
      await ensureActiveRoute(page);
      await page.reload();
      await expect(page.locator(".dashboard-layout")).toBeVisible({
        timeout: 15_000,
      });

      const liveMapBtn = page.locator(".btn-live-map");
      await expect(liveMapBtn).toBeVisible({ timeout: 10_000 });
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
