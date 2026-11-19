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

  test("a2: splitting never puts one postal code on two routes", async ({ page }) => {
    const token = await page.evaluate(() => localStorage.getItem("auth-token"));
    const headers = { Authorization: `Token ${token}` };
    const fs = await import("fs");
    const upload = await page.request.post(`${API_BASE}/upload/`, {
      headers,
      multipart: {
        file: {
          name: "zip_groups_60.csv",
          mimeType: "text/csv",
          buffer: fs.readFileSync(path.resolve(__dirname, "test-data/zip_groups_60.csv")),
        },
      },
    });
    const { id } = await upload.json();

    const split = await page.request.post(`${API_BASE}/sessions/${id}/cluster/`, {
      headers,
      data: { n_routes: 3 },
    });
    expect(split.status()).toBe(201);
    const body = await split.json();
    expect(body.sub_routes).toHaveLength(3);

    const routesByZip = new Map<string, Set<string>>();
    for (const route of body.sub_routes) {
      const detail = await (
        await page.request.get(`${API_BASE}/sessions/${route.id}/`, { headers })
      ).json();
      for (const stop of detail.stops) {
        const zip = String(stop.raw_address).slice(0, 4);
        routesByZip.set(zip, (routesByZip.get(zip) ?? new Set()).add(route.id));
      }
    }
    expect(routesByZip.size).toBe(6);
    for (const [zip, routes] of routesByZip) {
      expect(routes.size, `zip ${zip} is on ${routes.size} routes`).toBe(1);
    }
  });

  test("a3: moving a stop that splits a postal code shows the banner; resolving it hides it", async ({
    page,
  }) => {
    const token = await page.evaluate(() => localStorage.getItem("auth-token"));
    const headers = { Authorization: `Token ${token}` };
    const fs = await import("fs");
    const upload = await page.request.post(`${API_BASE}/upload/`, {
      headers,
      multipart: {
        file: {
          name: "a3_zip_groups.csv",
          mimeType: "text/csv",
          buffer: fs.readFileSync(path.resolve(__dirname, "test-data/zip_groups_60.csv")),
        },
      },
    });
    const { id } = await upload.json();
    const uniqueName = `Conflict Day ${Date.now()}`;
    await page.request.patch(`${API_BASE}/sessions/${id}/rename/`, {
      headers,
      data: { name: uniqueName },
    });
    const split = await page.request.post(`${API_BASE}/sessions/${id}/cluster/`, {
      headers,
      data: { n_routes: 3 },
    });
    expect((await split.json()).zip_conflicts).toEqual([]);

    const openReview = async () => {
      await page.goto("/");
      const card = page.locator(".dashboard-split .session-card", { hasText: uniqueName }).first();
      await expect(card).toBeVisible({ timeout: 30_000 });
      await card.locator(".session-card-info").click();
      await expect(page.locator(".cluster-review")).toBeVisible({ timeout: 15_000 });
    };

    await openReview();
    // Clean split: no banner (AC1).
    await expect(page.getByTestId("zip-conflict-banner")).toHaveCount(0);

    // Move one stop to another biker through the Move dialog.
    await page.locator(".numbered-marker").first().click({ force: true });
    await page.locator(".cluster-stop-popup").getByRole("button", { name: /^Move to/ }).click();
    const dialog = page.getByRole("dialog", { name: "Move stop to another biker" });
    await dialog.locator(".move-stop-option").first().click();

    const banner = page.getByTestId("zip-conflict-banner");
    await expect(banner).toBeVisible({ timeout: 10_000 });
    await expect(banner).toContainText("irányítószám több körben szerepel");
    await expect(banner).toContainText(/\d{4} \(.+: \d+, .+: \d+\)/);

    // Clicking a zip in the banner highlights its stops.
    await banner.locator(".cluster-zip-banner-item").first().click();
    await expect(page.locator(".cluster-stop-item--zip-highlight").first()).toBeVisible();

    // The API reports the same conflict; move the stray stop(s) back to resolve it.
    const parent = await (await page.request.get(`${API_BASE}/sessions/${id}/`, { headers })).json();
    expect(parent.zip_conflicts).toHaveLength(1);
    const [minor, major] = [...parent.zip_conflicts[0].routes].sort(
      (a: { count: number }, b: { count: number }) => a.count - b.count
    );
    const minorRoute = await (
      await page.request.get(`${API_BASE}/sessions/${minor.session_id}/`, { headers })
    ).json();
    for (const stop of minorRoute.stops.filter(
      (s: { postal_code: string }) => s.postal_code === parent.zip_conflicts[0].zip
    )) {
      const res = await page.request.post(`${API_BASE}/sessions/${minor.session_id}/move-stop/`, {
        headers,
        data: { stop_id: stop.id, to_session_id: major.session_id },
      });
      expect(res.status()).toBe(200);
    }

    await openReview();
    await expect(page.getByTestId("zip-conflict-banner")).toHaveCount(0);
  });

  test("a6: a zone that fits no biker whole is broken up by zip and labelled", async ({ page }) => {
    const token = await page.evaluate(() => localStorage.getItem("auth-token"));
    const headers = { Authorization: `Token ${token}` };
    const fs = await import("fs");
    const upload = await page.request.post(`${API_BASE}/upload/`, {
      headers,
      multipart: {
        file: {
          name: "zone_split_16.csv",
          mimeType: "text/csv",
          buffer: fs.readFileSync(path.resolve(__dirname, "test-data/zone_split_16.csv")),
        },
      },
    });
    const { id } = await upload.json();
    const uniqueName = `Zone Split Day ${Date.now()}`;
    await page.request.patch(`${API_BASE}/sessions/${id}/rename/`, { headers, data: { name: uniqueName } });
    const bikers = await (await page.request.get(`${API_BASE}/users/bikers/`, { headers })).json();
    const split = await page.request.post(`${API_BASE}/sessions/${id}/cluster/`, {
      headers,
      data: {
        assignments: bikers
          .slice(0, 2)
          .map((b: { id: number }) => ({ biker_id: b.id, target_stops: 0, window_minutes: 60 })),
      },
    });
    expect(split.status()).toBe(201);
    const body = await split.json();
    expect(body.unassigned_zones).toHaveLength(1);
    expect(body.split_zones).toHaveLength(1);

    await page.goto("/");
    const card = page.locator(".dashboard-split .session-card", { hasText: uniqueName }).first();
    await expect(card).toBeVisible({ timeout: 30_000 });
    await card.locator(".session-card-info").click();
    const label = page.getByTestId("split-zones");
    await expect(label).toBeVisible({ timeout: 15_000 });
    await expect(label).toContainText("Zóna Z12 szétbontva");
    await expect(label).toContainText(/1082→.+, 1083→/);
    // A whole zip is never divided: no zip warning.
    await expect(page.getByTestId("zip-conflict-banner")).toHaveCount(0);
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
  test("h3: a sub-route has no way back into the planner, so it cannot be re-split", async ({
    page,
  }) => {
    await page.getByRole("button", { name: "Upload Route" }).click();
    await uploadTestFile(page, "large_geocoded_60.csv");
    const modal = page.locator(".split-planner");
    await expect(modal).toBeVisible({ timeout: 10_000 });
    const checkedBikers = modal.locator(".split-planner-biker input:checked");
    while ((await checkedBikers.count()) > 0) {
      await checkedBikers.first().uncheck();
    }
    await modal.getByRole("button", { name: "Split automatically" }).click();
    await expect(page.locator(".cluster-review")).toBeVisible({ timeout: 30_000 });

    // Open one sub-route: it is shown on the map, without the "Route planner" button.
    await page.locator('button[title="View full route"]').first().click();
    await expect(page.locator(".cluster-review")).toBeHidden({ timeout: 15_000 });
    await expect(page.getByRole("button", { name: /Route planner/ })).toHaveCount(0);
  });
});
