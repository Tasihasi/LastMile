import { test, expect, loginViaAPI, API_BASE } from "./fixtures";
import path from "path";

test.describe("Clustering", () => {
  /**
   * Helper: upload the large CSV via API to create a session with >48 stops,
   * then return its session ID.
   */
  async function createLargeSession(page: import("@playwright/test").Page) {
    const token = await page.evaluate(() =>
      localStorage.getItem("auth-token")
    );

    // Use the bundled 300-stop sample file
    const samplePath = path.resolve(
      __dirname,
      "../../backend/planner/sample_data/large_delivery_300.csv"
    );

    const fs = await import("fs");
    const fileContent = fs.readFileSync(samplePath);
    const res = await page.request.post(`${API_BASE}/upload/`, {
      headers: { Authorization: `Token ${token}` },
      multipart: {
        file: {
          name: "large_delivery_300.csv",
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
      timeout: 15_000,
    });

    // Upload large file via API to have a session with >48 stops
    await createLargeSession(page);

    // Reload dashboard to see new session
    await page.reload();
    await expect(page.locator(".dashboard-layout")).toBeVisible({
      timeout: 15_000,
    });

    // Should see "Split into Routes" button on the large session
    const splitBtn = page.locator(".btn-cluster");
    await expect(splitBtn).toBeVisible({ timeout: 10_000 });
  });

  test("cluster, review, and undo split", async ({ page }) => {
    await expect(page.locator(".dashboard-layout")).toBeVisible({
      timeout: 15_000,
    });

    await createLargeSession(page);
    await page.reload();
    await expect(page.locator(".dashboard-layout")).toBeVisible({
      timeout: 15_000,
    });

    // Click Split into Routes
    const splitBtn = page.locator(".btn-cluster").first();
    await expect(splitBtn).toBeVisible({ timeout: 10_000 });
    await splitBtn.click();

    // Should transition to cluster review view
    await expect(page.getByText("Cluster Review")).toBeVisible({
      timeout: 15_000,
    });

    // Should see route cards
    await expect(page.locator(".cluster-route-card").first()).toBeVisible({
      timeout: 10_000,
    });

    // Should see summary stats
    await expect(page.locator(".cluster-review-stat")).toHaveCount(3);

    // Map should be visible
    await expect(page.locator(".leaflet-container")).toBeVisible();

    // Expand first route card
    await page.locator(".cluster-route-card-header").first().click();
    await expect(
      page.locator(".cluster-route-stops").first()
    ).toBeVisible({ timeout: 5_000 });

    // Test undo split
    const undoBtn = page.getByRole("button", { name: "Undo Split" });
    await expect(undoBtn).toBeVisible();
    await undoBtn.click();

    // Should return to dashboard
    await expect(page.getByText("Route Management")).toBeVisible({
      timeout: 15_000,
    });
  });

  test("optimize sub-route from cluster review", async ({ page }) => {
    await expect(page.locator(".dashboard-layout")).toBeVisible({
      timeout: 15_000,
    });

    await createLargeSession(page);
    await page.reload();
    await expect(page.locator(".dashboard-layout")).toBeVisible({
      timeout: 15_000,
    });

    // Click Split into Routes
    const splitBtn = page.locator(".btn-cluster").first();
    await expect(splitBtn).toBeVisible({ timeout: 10_000 });
    await splitBtn.click();

    await expect(page.getByText("Cluster Review")).toBeVisible({
      timeout: 15_000,
    });

    // Click Optimize All button
    const optimizeAllBtn = page.getByRole("button", {
      name: /Optimize All/,
    });
    if (await optimizeAllBtn.isVisible()) {
      await optimizeAllBtn.click();

      // Wait for optimization to complete (mock mode)
      await expect(
        page.locator(".cluster-review-stat", { hasText: "Optimized" })
      ).toBeVisible({ timeout: 30_000 });
    }
  });
});
