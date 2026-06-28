import { test, expect, loginViaAPI, uploadTestFile } from "./fixtures";

/**
 * Full real-world file journey for the company's UPS courier route sheet.
 *
 * Uses `ups_terkep_teszt.xlsx`, a committed fixture that reproduces the exact
 * signature of the gitignored operational file `example_files/UPS térkép
 * teszt.xlsx`: Hungarian headers (város, irszám, u, hsz, megj, Cím, kör), a
 * per-courier summary count row, a postal-code column, and an address column
 * built from an uncalculated Excel formula. We log in as one of the real
 * courier profiles ("bálint") for authenticity.
 *
 * Asserts the whole pipeline works on this signature: upload -> geocode ->
 * optimize -> route geometry encoded on the map -> deliveries completed.
 */
test.describe("UPS courier file — full journey", () => {
  test("upload, geocode, optimize, encode map, complete route", async ({
    page,
  }) => {
    // Log in as the courier "bálint" (one of the profiles in the real sheet).
    await loginViaAPI(page, "bálint", "biker");

    // Start a new route and upload the real-signature UPS file.
    await page.getByRole("button", { name: "New Route" }).click();
    await expect(page.locator('input[type="file"]')).toBeAttached({
      timeout: 10_000,
    });
    await uploadTestFile(page, "ups_terkep_teszt.xlsx");

    // All 14 courier stops parse out of the sheet (summary row dropped).
    await expect(page.locator(".stop-item")).toHaveCount(14, {
      timeout: 15_000,
    });

    // The sheet has no coordinates, so geocoding is required first.
    const geocodeBtn = page.getByRole("button", { name: "Geocode Addresses" });
    await expect(geocodeBtn).toBeVisible();
    await geocodeBtn.click();
    // Progress span reads e.g. "Geocoding 2/14..." (distinct from the disabled
    // "Geocoding..." button label).
    await expect(page.getByText(/Geocoding \d+\/\d+/)).toBeVisible();

    // Once geocoded (mock mode is instant), optimization becomes available.
    const optimizeBtn = page.getByRole("button", { name: "Optimize Route" });
    await expect(optimizeBtn).toBeVisible({ timeout: 30_000 });
    await optimizeBtn.click();

    // Route is optimized: summary with duration/distance appears.
    await expect(page.locator(".route-summary")).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.locator(".route-summary-item")).toHaveCount(3);

    // The map is "encoded": numbered markers + the route geometry polyline
    // (rendered as an SVG path in Leaflet's overlay pane) are drawn.
    await expect(page.locator(".leaflet-container")).toBeVisible();
    await expect(page.locator(".numbered-marker").first()).toBeVisible({
      timeout: 10_000,
    });
    await expect(
      page.locator(".leaflet-overlay-pane path").first()
    ).toBeAttached({ timeout: 10_000 });

    // Start the route and complete every delivery.
    const startBtn = page.getByRole("button", { name: "Start Route" });
    await expect(startBtn).toBeVisible();
    await startBtn.click();
    await expect(page.locator(".route-status-banner--active")).toBeVisible({
      timeout: 10_000,
    });

    // Mark each stop delivered until none remain.
    let deliverBtns = page.locator(".stop-action-btn--delivered");
    while ((await deliverBtns.count()) > 0) {
      await deliverBtns.first().click();
      await page.waitForTimeout(300);
      deliverBtns = page.locator(".stop-action-btn--delivered");
    }

    // Route is complete: the finished banner is shown.
    await expect(page.locator(".route-status-banner--finished")).toBeVisible({
      timeout: 15_000,
    });
  });
});
