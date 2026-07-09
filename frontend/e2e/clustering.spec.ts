import { test, expect, loginViaAPI, API_BASE } from "./fixtures";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

test.describe("Clustering", () => {
  // Clustering 300 stops is heavy — give extra time
  test.setTimeout(120_000);

  /**
   * Helper: upload the large CSV via API to create a session with >48 stops,
   * then return its session ID.
   */
  async function createLargeSession(page: import("@playwright/test").Page) {
    const token = await page.evaluate(() =>
      localStorage.getItem("auth-token")
    );

    const samplePath = path.resolve(
      __dirname,
      "test-data/large_geocoded_60.csv"
    );

    const fs = await import("fs");
    const fileContent = fs.readFileSync(samplePath);
    const res = await page.request.post(`${API_BASE}/upload/`, {
      headers: { Authorization: `Token ${token}` },
      multipart: {
        file: {
          name: "large_geocoded_60.csv",
          mimeType: "text/csv",
          buffer: fileContent,
        },
      },
    });
    const data = await res.json();
    return data.id as string;
  }

  test.beforeEach(async ({ page }) => {
    await loginViaAPI(page, "Planner", "planner");
  });

  test("split into routes button visible for large uploads", async ({
    page,
  }) => {
    await expect(page.locator(".dashboard-layout")).toBeVisible({
      timeout: 20_000,
    });

    await createLargeSession(page);
    await page.reload();
    await page.waitForLoadState("networkidle");
    await expect(page.locator(".dashboard-layout")).toBeVisible({
      timeout: 20_000,
    });

    const splitBtn = page.locator(".cluster-banner").first();
    await expect(splitBtn).toBeVisible({ timeout: 20_000 });
  });

  test("split produces independent sub-route cards in Unassigned", async ({
    page,
  }) => {
    await expect(page.locator(".dashboard-layout")).toBeVisible({
      timeout: 20_000,
    });

    await createLargeSession(page);
    await page.reload();
    await page.waitForLoadState("networkidle");
    await expect(page.locator(".dashboard-layout")).toBeVisible({
      timeout: 20_000,
    });

    // Count unassigned cards before split
    const unassignedCards = page.locator(".dashboard-unassigned .session-card");
    const beforeCount = await unassignedCards.count();

    const splitBtn = page.locator(".cluster-banner").first();
    await expect(splitBtn).toBeVisible({ timeout: 20_000 });
    await splitBtn.click();

    // The split planner modal opens. Deselect every biker so the split is
    // automatic and the sub-routes land in the Unassigned column.
    const modal = page.locator(".split-planner");
    await expect(modal).toBeVisible({ timeout: 10_000 });
    const checkedBikers = modal.locator(".split-planner-biker input:checked");
    while ((await checkedBikers.count()) > 0) {
      await checkedBikers.first().uncheck();
    }
    await modal.getByRole("button", { name: "Split automatically" }).click();

    // After splitting, the app opens the split review screen for fine-tuning.
    await expect(page.locator(".cluster-review")).toBeVisible({
      timeout: 30_000,
    });

    // Back to the dashboard: sub-route cards show up in the Unassigned column.
    await page.locator(".cluster-review-header .btn-ghost", { hasText: "Dashboard" }).click();
    await expect(page.getByText("Route Management")).toBeVisible({
      timeout: 30_000,
    });

    // Parent card should be gone; sub-routes replace it.
    await expect
      .poll(async () => unassignedCards.count(), { timeout: 30_000 })
      .toBeGreaterThan(beforeCount);

    // Sub-routes use the "{parent_name}_N" naming convention.
    const subRouteCard = page
      .locator(".dashboard-unassigned .session-card-name", {
        hasText: /_\d+$/,
      })
      .first();
    await expect(subRouteCard).toBeVisible({ timeout: 10_000 });
  });
});
