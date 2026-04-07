import { test, expect, loginViaAPI } from "./fixtures";

test.describe("Session List (Biker)", () => {
  test("shows seeded sessions for Anna", async ({ page }) => {
    await loginViaAPI(page, "Anna", "biker");

    // Should see session list
    await expect(page.getByText("Recent Routes")).toBeVisible({
      timeout: 15_000,
    });

    // Anna has seeded routes
    const sessions = page.locator(".session-list-item");
    await expect(sessions.first()).toBeVisible({ timeout: 10_000 });
    expect(await sessions.count()).toBeGreaterThan(0);
  });

  test("shows new route button", async ({ page }) => {
    await loginViaAPI(page, "Anna", "biker");
    await expect(page.getByText("Recent Routes")).toBeVisible({
      timeout: 15_000,
    });

    await expect(
      page.getByRole("button", { name: "New Route" })
    ).toBeVisible();
  });

  test("active sessions show green dot", async ({ page }) => {
    await loginViaAPI(page, "Anna", "biker");
    await expect(page.getByText("Recent Routes")).toBeVisible({
      timeout: 15_000,
    });

    // Anna has an in_progress route from seed data
    const activeDot = page.locator(".session-list-item-dot");
    if (await activeDot.first().isVisible()) {
      // Active session shows progress text
      await expect(
        page.locator(".session-list-item-status").first()
      ).toBeVisible();
    }
  });

  test("finished routes are in collapsible section", async ({ page }) => {
    await loginViaAPI(page, "Anna", "biker");
    await expect(page.getByText("Recent Routes")).toBeVisible({
      timeout: 15_000,
    });

    // Anna has a finished route from seed data
    const finishedToggle = page.locator(".session-list-finished-toggle");
    if (await finishedToggle.isVisible()) {
      await finishedToggle.click();
      await expect(
        page.locator(".session-list-item--finished").first()
      ).toBeVisible({ timeout: 5_000 });
    }
  });

  test("clicking session loads route view", async ({ page }) => {
    await loginViaAPI(page, "Anna", "biker");
    await expect(page.getByText("Recent Routes")).toBeVisible({
      timeout: 15_000,
    });

    const session = page.locator(".session-list-item").first();
    await expect(session).toBeVisible({ timeout: 10_000 });
    await session.click();

    // Should load route with stops and map
    await expect(page.locator(".stop-item").first()).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.locator(".leaflet-container")).toBeVisible();
  });

  test("empty state for new biker", async ({ page }) => {
    await loginViaAPI(page, "NewBikerNoRoutes", "biker");
    await expect(
      page.getByText(/No routes yet/)
    ).toBeVisible({ timeout: 15_000 });
  });
});
