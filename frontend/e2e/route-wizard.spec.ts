import path from "path";
import { fileURLToPath } from "url";
import { test, expect, loginViaAPI, uploadTestFile, TEST_FILES } from "./fixtures";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

test.describe("Route planning wizard", () => {
  test.beforeEach(async ({ page }) => {
    await loginViaAPI(page, "BikerWizard", "biker");
    await page.getByRole("button", { name: "New Route" }).click();
  });

  test("merges several files into one route and steps back and forth", async ({
    page,
  }) => {
    await page
      .locator('input[type="file"]')
      .setInputFiles([TEST_FILES.needsGeocoding, TEST_FILES.geocoded]);
    await expect(page.locator(".wizard-file")).toHaveCount(2);

    await page.getByRole("button", { name: /Upload & continue/ }).click();

    // Step 2: geocoding finishes, all stops from both files are counted.
    const next = page.locator(".wizard-footer").getByRole("button", { name: /Review addresses/ });
    await expect(next).toBeEnabled({ timeout: 30_000 });
    await expect(page.locator(".wizard-stat--ok strong")).not.toHaveText("0");

    // Step 3 -> back to 2 -> back to 1: the picked files are kept.
    await next.click();
    await expect(page.getByText("Every address was found")).toBeVisible();
    await page.locator(".wizard-footer").getByRole("button", { name: /Geocoding/ }).click();
    await page.locator(".wizard-footer").getByRole("button", { name: /Files/ }).click();
    await expect(page.locator(".wizard-file")).toHaveCount(2);

    // Removing a file re-imports on the way forward.
    await page.getByRole("button", { name: /^Remove/ }).first().click();
    await expect(page.locator(".wizard-file")).toHaveCount(1);
    await page.getByRole("button", { name: /Upload & continue/ }).click();
    await expect(page.locator(".wizard-footer").getByRole("button", { name: /Review addresses/ })).toBeEnabled({
      timeout: 30_000,
    });

    // Forward to the optimize step, then back via the stepper.
    await page.locator(".wizard-footer").getByRole("button", { name: /Review addresses/ }).click();
    await page.locator(".wizard-footer").getByRole("button", { name: /^Continue/ }).click();
    await page.locator(".wizard-footer").getByRole("button", { name: /^Continue/ }).click();
    await expect(page.getByRole("button", { name: "Optimize Route" })).toBeVisible();
    await page.getByRole("button", { name: /Fix addresses/ }).click();
    await expect(page.getByRole("heading", { name: "Fix addresses" })).toBeVisible();
  });

  test("postal-code step: untick a code, move an address, plan only the rest", async ({
    page,
  }) => {
    await page
      .locator('input[type="file"]')
      .setInputFiles(path.resolve(__dirname, "test-data", "postal_codes.csv"));
    await page.getByRole("button", { name: /Upload & continue/ }).click();
    const footer = page.locator(".wizard-footer");
    await expect(footer.getByRole("button", { name: /Review addresses/ })).toBeEnabled({
      timeout: 30_000,
    });
    await footer.getByRole("button", { name: /Review addresses/ }).click();
    await footer.getByRole("button", { name: /^Continue/ }).click();

    // Three postal codes found.
    await expect(page.locator(".postal-group")).toHaveCount(3);
    await expect(page.getByText("4 of 4 stops included")).toBeVisible();

    // Open 1052 and move Bravo to 1061.
    await page.getByRole("button", { name: "Show addresses for 1052" }).click();
    await page.getByLabel("Move Bravo to another postal code").selectOption("1061");
    await expect(page.locator(".postal-group-head").filter({ hasText: "1061" })).toContainText("2 stops");

    // Untick 1111 (Delta): 3 stops stay in the plan.
    await page.getByLabel("Include postal code 1111").uncheck();
    await expect(page.getByText("3 of 4 stops included")).toBeVisible();

    // Back and forth keeps the choice.
    await footer.getByRole("button", { name: /Fix addresses/ }).click();
    await footer.getByRole("button", { name: /^Continue/ }).click();
    await expect(page.getByText("3 of 4 stops included")).toBeVisible();

    // Optimize step only shows the included stops.
    await footer.getByRole("button", { name: /^Continue/ }).click();
    await expect(page.locator(".stop-item")).toHaveCount(3);
  });
  test("rename the route and go back from the map to the planning steps", async ({
    page,
  }) => {
    await uploadTestFile(page, "postal_codes.csv");
    await expect(page.getByRole("button", { name: "Optimize Route" })).toBeVisible();

    // Rename from the header.
    await page.getByRole("button", { name: /^Rename route/ }).click();
    const input = page.getByLabel("Route name");
    await input.fill("Monday morning");
    await input.press("Enter");
    await expect(page.getByRole("button", { name: "Rename route Monday morning" })).toBeVisible();

    // Reopen the route from the biker's list: it is unplanned, so it opens in the wizard.
    await page.reload();
    await page.getByRole("button", { name: /Monday morning/ }).first().click();
    await expect(page.getByText(/\d+ of \d+ stops included/)).toBeVisible();

    // Continue to the map, then use the back button to return to the planning steps.
    await page.locator(".wizard-footer").getByRole("button", { name: /^Continue/ }).click();
    await expect(page.getByRole("button", { name: "Optimize Route" })).toBeVisible();
    await page.getByRole("button", { name: "Postal codes" }).click();
    await expect(page.getByText(/\d+ of \d+ stops included/)).toBeVisible();
  });
  test("an optimized route reopened from the list reopens at the latest planning step", async ({
    page,
  }) => {
    await uploadTestFile(page, "postal_codes.csv");
    await page.getByRole("button", { name: "Optimize Route" }).click();
    await expect(page.locator(".route-summary")).toBeVisible({ timeout: 30_000 });

    // Reopening drops the biker at the latest planning step (the map) ...
    await page.reload();
    await page.locator(".session-list-item").first().click();
    await expect(page.locator(".route-summary")).toBeVisible();

    // ... and the earlier steps stay one click away.
    await page.getByRole("button", { name: /Postal codes/ }).click();
    await expect(page.getByText(/\d+ of \d+ stops included/)).toBeVisible();
  });
});
