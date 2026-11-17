import { test, expect, loginViaAPI, API_BASE } from "./fixtures";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

test.describe("Move zip", () => {
  test.setTimeout(120_000);

  test("a4: Move zip… from the conflict banner puts the whole zip on one route", async ({ page }) => {
    await loginViaAPI(page, "Planner", "planner");
    const token = await page.evaluate(() => localStorage.getItem("auth-token"));
    const headers = { Authorization: `Token ${token}` };
    const fs = await import("fs");
    const upload = await page.request.post(`${API_BASE}/upload/`, {
      headers,
      multipart: {
        file: {
          name: "a4_zip_groups.csv",
          mimeType: "text/csv",
          buffer: fs.readFileSync(path.resolve(__dirname, "test-data/zip_groups_60.csv")),
        },
      },
    });
    const { id } = await upload.json();
    const uniqueName = `Move Zip Day ${Date.now()}`;
    await page.request.patch(`${API_BASE}/sessions/${id}/rename/`, { headers, data: { name: uniqueName } });
    const split = await page.request.post(`${API_BASE}/sessions/${id}/cluster/`, { headers, data: { n_routes: 3 } });
    const { sub_routes: routes } = await split.json();

    // Create a conflict: one stop of a zip goes to another route.
    const first = await (await page.request.get(`${API_BASE}/sessions/${routes[0].id}/`, { headers })).json();
    const stop = first.stops[0];
    const zip = stop.postal_code as string;
    const move = await page.request.post(`${API_BASE}/sessions/${routes[0].id}/move-stop/`, {
      headers,
      data: { stop_id: stop.id, to_session_id: routes[1].id },
    });
    expect((await move.json()).zip_conflicts).toHaveLength(1);

    await page.goto("/");
    const card = page.locator(".dashboard-split .session-card", { hasText: uniqueName }).first();
    await expect(card).toBeVisible({ timeout: 30_000 });
    await card.locator(".session-card-info").click();
    const banner = page.getByTestId("zip-conflict-banner");
    await expect(banner).toBeVisible({ timeout: 15_000 });

    await banner.getByRole("button", { name: "Move zip…" }).first().click();
    const dialog = page.getByRole("dialog", { name: "Move postal code to another biker" });
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText(zip);
    // The dialog shows resulting counts before confirming.
    await expect(dialog.locator(".move-stop-meta").first()).toContainText(/\d+ → \d+ stops|already has all/);
    await dialog.locator(".move-stop-option:not([disabled])").first().click();

    // No reload: banner disappears, API agrees.
    await expect(banner).toHaveCount(0, { timeout: 10_000 });
    const parent = await (await page.request.get(`${API_BASE}/sessions/${id}/`, { headers })).json();
    expect(parent.zip_conflicts).toEqual([]);
  });
});
