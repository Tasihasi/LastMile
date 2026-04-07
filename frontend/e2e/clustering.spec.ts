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
      timeout: 20_000,
    });

    await createLargeSession(page);
    await page.reload();
    await page.waitForLoadState("networkidle");
    await expect(page.locator(".dashboard-layout")).toBeVisible({
      timeout: 20_000,
    });

    const splitBtn = page.locator(".btn-cluster");
    await expect(splitBtn).toBeVisible({ timeout: 20_000 });
  });

  test("cluster, review, and undo split", async ({ page }) => {
    await expect(page.locator(".dashboard-layout")).toBeVisible({
      timeout: 20_000,
    });

    await createLargeSession(page);
    await page.reload();
    await page.waitForLoadState("networkidle");
    await expect(page.locator(".dashboard-layout")).toBeVisible({
      timeout: 20_000,
    });

    // Click Split into Routes — KMeans on 300 stops takes time
    const splitBtn = page.locator(".btn-cluster").first();
    await expect(splitBtn).toBeVisible({ timeout: 20_000 });
    await splitBtn.click();

    // Wait for cluster review (backend clustering + frontend transition)
    await expect(page.getByText("Cluster Review")).toBeVisible({
      timeout: 30_000,
    });

    await expect(page.locator(".cluster-route-card").first()).toBeVisible({
      timeout: 15_000,
    });

    await expect(page.locator(".cluster-review-stat").first()).toBeVisible();
    await expect(page.locator(".leaflet-container")).toBeVisible();

    // Expand first route card
    await page.locator(".cluster-route-card-header").first().click();
    await expect(
      page.locator(".cluster-route-stops").first()
    ).toBeVisible({ timeout: 10_000 });

    // Undo split
    const undoBtn = page.getByRole("button", { name: "Undo Split" });
    await expect(undoBtn).toBeVisible();
    await undoBtn.click();

    await expect(page.getByText("Route Management")).toBeVisible({
      timeout: 20_000,
    });
  });

  test("optimize sub-route from cluster review", async ({ page }) => {
    await expect(page.locator(".dashboard-layout")).toBeVisible({
      timeout: 20_000,
    });

    await createLargeSession(page);
    await page.reload();
    await page.waitForLoadState("networkidle");
    await expect(page.locator(".dashboard-layout")).toBeVisible({
      timeout: 20_000,
    });

    const splitBtn = page.locator(".btn-cluster").first();
    await expect(splitBtn).toBeVisible({ timeout: 20_000 });
    await splitBtn.click();

    await expect(page.getByText("Cluster Review")).toBeVisible({
      timeout: 30_000,
    });

    // Click Optimize All if visible
    const optimizeAllBtn = page.getByRole("button", {
      name: /Optimize All/,
    });
    if (await optimizeAllBtn.isVisible({ timeout: 10_000 }).catch(() => false)) {
      await optimizeAllBtn.click();

      await expect(
        page.locator(".cluster-review-stat", { hasText: "Optimized" })
      ).toBeVisible({ timeout: 60_000 });
    }
  });
});
