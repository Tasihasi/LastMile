import { test, expect, loginViaAPI, uploadTestFile, API_BASE } from "./fixtures";
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

  test("large uploads have no split button on the dashboard (splitting is a wizard step)", async ({
    page,
  }) => {
    await createLargeSession(page);
    await page.reload();
    await expect(page.locator(".dashboard-layout")).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.locator(".session-card").first()).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.locator(".cluster-banner")).toHaveCount(0);
  });

  test("a split route is one card for the planner; the bikers get the sub-routes", async ({
    page,
  }) => {
    await expect(page.locator(".dashboard-layout")).toBeVisible({
      timeout: 20_000,
    });

    // Upload through the wizard: files -> geocode -> fix -> postal codes -> bikers.
    await page.getByRole("button", { name: "Upload Route" }).click();
    await uploadTestFile(page, "large_geocoded_60.csv");

    const modal = page.locator(".split-planner");
    await expect(modal).toBeVisible({ timeout: 10_000 });
    const checkedBikers = modal.locator(".split-planner-biker input:checked");
    while ((await checkedBikers.count()) > 0) {
      await checkedBikers.first().uncheck();
    }
    await modal.getByRole("button", { name: "Split automatically" }).click();

    // The split review opens, still at the last planning step.
    await expect(page.locator(".cluster-review")).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.locator(".wizard-stepper")).toBeVisible();

    // Back on the dashboard: ONE card for the split route, listing its sub-routes.
    await page.locator(".cluster-review-header .btn-ghost", { hasText: "Dashboard" }).click();
    await expect(page.getByText("Route Management")).toBeVisible({
      timeout: 30_000,
    });
    const splitCard = page.locator(".dashboard-split .session-card").first();
    await expect(splitCard).toBeVisible({ timeout: 30_000 });
    await expect(splitCard.locator(".session-card-subroutes li").first()).toBeVisible();
    // Sub-routes are not listed as separate cards.
    await expect(
      page.locator(".session-card-name", { hasText: /_\d+$/ })
    ).toHaveCount(0);

    // Clicking the card lands on the split review, not on a map of a sub-route.
    await splitCard.locator(".session-card-info").click();
    await expect(page.locator(".cluster-review")).toBeVisible({
      timeout: 15_000,
    });

    // A stop's popup names the biker who carries it; "Move to…" opens a
    // window over the map to pick a different biker.
    await page.locator(".numbered-marker").first().click({ force: true });
    const popup = page.locator(".cluster-stop-popup");
    await expect(popup).toContainText("Carried by");
    await popup.getByRole("button", { name: "Stop details" }).click();
    const details = page.getByRole("dialog", { name: "Stop details" });
    await expect(details).toContainText("Carried by");
    await expect(details.locator(".stop-details-status")).toBeVisible();
    await details.getByRole("button", { name: "Close" }).click();
    await expect(details).toBeHidden();

    await popup.getByRole("button", { name: /^Move to/ }).click();
    const dialog = page.getByRole("dialog", { name: "Move stop to another biker" });
    await expect(dialog).toBeVisible();
    await expect(dialog.locator(".move-stop-option").first()).toBeVisible();
  });
});
