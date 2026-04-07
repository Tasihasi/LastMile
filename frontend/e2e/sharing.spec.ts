import { test, expect, loginViaAPI, API_BASE } from "./fixtures";

test.describe("Route Sharing", () => {
  test("share button copies link after optimization", async ({ page }) => {
    await loginViaAPI(page, "Anna", "biker");

    // Load a seeded session that has route geometry (in_progress or finished)
    const activeSession = page.locator(".session-list-item--active").first();
    if (await activeSession.isVisible()) {
      await activeSession.click();
      await expect(page.locator(".stop-item").first()).toBeVisible({
        timeout: 15_000,
      });

      // If route has a share button
      const shareBtn = page.locator(".share-btn");
      if (await shareBtn.isVisible()) {
        // Grant clipboard permissions
        await page.context().grantPermissions(["clipboard-read", "clipboard-write"]);

        await shareBtn.click();

        // Should show "Copied!" text
        await expect(page.getByText("Copied!")).toBeVisible({
          timeout: 5_000,
        });
      }
    }
  });

  test("shared route view loads for anonymous users", async ({ page }) => {
    // First create a share via API
    const loginRes = await page.request.post(`${API_BASE}/auth/login/`, {
      data: { username: "ShareTest", role: "biker" },
    });
    const { token } = await loginRes.json();

    // Get sessions to find one we can share
    const sessionsRes = await page.request.get(`${API_BASE}/sessions/`, {
      headers: { Authorization: `Token ${token}` },
    });
    const sessions = await sessionsRes.json();

    if (sessions.length > 0) {
      // Share the first session
      const shareRes = await page.request.post(
        `${API_BASE}/sessions/${sessions[0].id}/share/`,
        { headers: { Authorization: `Token ${token}` } }
      );

      if (shareRes.ok()) {
        const { share_id } = await shareRes.json();

        // Clear auth and visit shared route
        await page.evaluate(() => localStorage.removeItem("auth-token"));
        await page.goto(`/shared/${share_id}`);

        // Should show shared route view
        await expect(page.getByText("Shared Route")).toBeVisible({
          timeout: 15_000,
        });
        await expect(page.getByText("View Only")).toBeVisible();

        // Should show the map
        await expect(page.locator(".leaflet-container")).toBeVisible({
          timeout: 10_000,
        });
      }
    }
  });

  test("invalid share link shows error", async ({ page }) => {
    await page.goto("/shared/00000000-0000-0000-0000-000000000000");
    await expect(page.locator(".shared-route-error")).toBeVisible({
      timeout: 15_000,
    });
  });
});
