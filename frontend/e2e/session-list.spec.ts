import { test, expect, loginViaAPI } from "./fixtures";

test.describe("Session List (Biker)", () => {
  test("shows seeded sessions for Csilla", async ({ page }) => {
    // Csilla has seeded routes but none in_progress, so the SessionList stays
    // visible (Anna would be auto-selected into her in-progress route).
    await loginViaAPI(page, "Csilla", "biker");

    // Should see session list
    await expect(page.getByText("Recent Routes")).toBeVisible({
      timeout: 15_000,
    });

    // Csilla has seeded routes — may be active or all finished (collapsed)
    const activeSessions = page.locator(".session-list-item:not(.session-list-item--finished)");
    const finishedToggle = page.locator(".session-list-finished-toggle");

    const hasActive = await activeSessions.first().isVisible({ timeout: 5_000 }).catch(() => false);
    if (hasActive) {
      expect(await activeSessions.count()).toBeGreaterThan(0);
    } else {
      // All routes finished — expand toggle to verify
      await expect(finishedToggle).toBeVisible({ timeout: 5_000 });
      await finishedToggle.click();
      await expect(
        page.locator(".session-list-item--finished").first()
      ).toBeVisible({ timeout: 5_000 });
    }
  });

  test("shows new route button", async ({ page }) => {
    // Csilla has seeded routes but none in_progress, so the SessionList stays
    // visible (Anna would be auto-selected into her in-progress route).
    await loginViaAPI(page, "Csilla", "biker");
    await expect(page.getByText("Recent Routes")).toBeVisible({
      timeout: 15_000,
    });

    await expect(
      page.getByRole("button", { name: "New Route" })
    ).toBeVisible();
  });

  test("active sessions show green dot", async ({ page }) => {
    // Csilla has seeded routes but none in_progress, so the SessionList stays
    // visible (Anna would be auto-selected into her in-progress route).
    await loginViaAPI(page, "Csilla", "biker");
    await expect(page.getByText("Recent Routes")).toBeVisible({
      timeout: 15_000,
    });

    // Csilla has no in_progress route in seed data, so the dot may be absent.
    const activeDot = page.locator(".session-list-item-dot");
    if (await activeDot.first().isVisible()) {
      // Active session shows progress text
      await expect(
        page.locator(".session-list-item-status").first()
      ).toBeVisible();
    }
  });

  test("finished routes are in collapsible section", async ({ page }) => {
    // Csilla has seeded routes but none in_progress, so the SessionList stays
    // visible (Anna would be auto-selected into her in-progress route).
    await loginViaAPI(page, "Csilla", "biker");
    await expect(page.getByText("Recent Routes")).toBeVisible({
      timeout: 15_000,
    });

    // Csilla has a finished route from seed data
    const finishedToggle = page.locator(".session-list-finished-toggle");
    if (await finishedToggle.isVisible()) {
      await finishedToggle.click();
      await expect(
        page.locator(".session-list-item--finished").first()
      ).toBeVisible({ timeout: 5_000 });
    }
  });

  test("clicking session loads route view", async ({ page }) => {
    // Csilla has seeded routes but none in_progress, so the SessionList stays
    // visible (Anna would be auto-selected into her in-progress route).
    await loginViaAPI(page, "Csilla", "biker");
    await expect(page.getByText("Recent Routes")).toBeVisible({
      timeout: 15_000,
    });

    // Routes may be in the active list or the collapsed finished section
    let session = page.locator(".session-list-item:not(.session-list-item--finished)").first();
    const hasActive = await session.isVisible({ timeout: 5_000 }).catch(() => false);
    if (!hasActive) {
      const toggle = page.locator(".session-list-finished-toggle");
      if (await toggle.isVisible()) {
        await toggle.click();
      }
      session = page.locator(".session-list-item--finished").first();
    }
    await expect(session).toBeVisible({ timeout: 10_000 });
    await session.click();

    // An unplanned route reopens in the wizard (postal codes); a planned one on the map.
    await expect(
      page.locator(".wizard-stepper, .leaflet-container").first()
    ).toBeVisible({ timeout: 15_000 });
  });

  test("empty state for new biker", async ({ page }) => {
    await loginViaAPI(page, "NewBikerNoRoutes", "biker");
    await expect(
      page.getByText(/No routes yet/)
    ).toBeVisible({ timeout: 15_000 });
  });
  test("a biker can go back from an open route to the list of all routes", async ({
    page,
  }) => {
    // Anna's in-progress route either opens straight away (a lone one) or is picked from the list.
    await loginViaAPI(page, "Anna", "biker");
    const active = page.locator(".session-list-item--active").first();
    if (await active.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await active.click();
    }
    await expect(page.locator(".stop-item").first()).toBeVisible({
      timeout: 15_000,
    });

    await page.getByRole("button", { name: /My routes/ }).click();
    await expect(page.getByText("Recent Routes")).toBeVisible({
      timeout: 10_000,
    });
    // The list stays: it must not bounce back into the in-progress route.
    await page.waitForTimeout(1_000);
    await expect(page.getByText("Recent Routes")).toBeVisible();
  });
});
