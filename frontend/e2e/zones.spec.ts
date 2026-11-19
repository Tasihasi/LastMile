import { test, expect, loginViaAPI, uploadTestFile, API_BASE } from "./fixtures";

test.describe("Zones (main menu)", () => {
  test.setTimeout(90_000);

  test("planner adds, rejects an overlap, edits and deletes a zone", async ({ page }) => {
    await loginViaAPI(page, "Planner", "planner");
    await page.getByRole("button", { name: "Zones" }).click();
    const dialog = page.getByRole("dialog", { name: "Zones" });
    const items = dialog.getByTestId("zone-item");
    await expect(items.first()).toBeVisible();
    const before = await items.count();

    // A postal code can live in only one zone.
    await dialog.getByRole("button", { name: "+ Add zone" }).click();
    await dialog.getByLabel("Zone postal codes").fill("1201, 1082");
    await dialog.getByRole("button", { name: "Save zone" }).click();
    await expect(dialog.getByRole("alert")).toContainText("1082 already belongs to zone");
    await expect(items).toHaveCount(before);

    // Add a free zone, then edit it.
    await dialog.getByLabel("Zone name").fill("E2E outer");
    await dialog.getByLabel("Zone postal codes").fill("1201, 1202");
    await dialog.getByRole("button", { name: "Save zone" }).click();
    await expect(items).toHaveCount(before + 1);
    const mine = items.filter({ hasText: "E2E outer" });
    await expect(mine).toContainText("1202");
    await mine.getByRole("button", { name: "Edit" }).click();
    await dialog.getByLabel("Zone postal codes").fill("1201");
    await dialog.getByRole("button", { name: "Save zone" }).click();
    await expect(mine).not.toContainText("1202");

    // The server agrees, and deleting frees the code again.
    const token = await page.evaluate(() => localStorage.getItem("auth-token"));
    const headers = { Authorization: `Token ${token}` };
    const zones = (await (await page.request.get(`${API_BASE}/zones/`, { headers })).json()).zones;
    expect(zones.find((z: { name: string }) => z.name === "E2E outer").zips).toEqual(["1201"]);
    await mine.getByRole("button", { name: /Delete zone/ }).click();
    await expect(items).toHaveCount(before);
  });

  test("split dialog no longer offers a single zip/district lock", async ({ page }) => {
    await loginViaAPI(page, "Planner", "planner");
    await page.getByRole("button", { name: /Upload Route/ }).first().click();
    await uploadTestFile(page, "zone_split_16.csv");
    const dialog = page.getByRole("dialog", { name: "Split route planner" });
    await expect(dialog.getByText("Plan by available time")).toBeVisible();
    await expect(dialog.getByText("Single zip/district")).toHaveCount(0);
  });
});
