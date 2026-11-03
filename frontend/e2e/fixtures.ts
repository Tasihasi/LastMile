import { test as base, expect, type Page } from "@playwright/test";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const API_BASE = "http://localhost:8000/api";

/** Helper: log in via the UI and return the authenticated page. */
async function loginViaUI(
  page: Page,
  username: string,
  role: "biker" | "planner"
) {
  await page.goto("/");
  await page.getByLabel("Username").fill(username);
  await page.getByRole("button", { name: role, exact: false }).click();
  await page.getByRole("button", { name: "Sign In" }).click();
  // Wait for the app to fully load after login (dashboard or session list)
  await expect(page.locator("h1", { hasText: "LastMile" })).toBeVisible({
    timeout: 15_000,
  });
  await page.waitForLoadState("networkidle");
}

/** Helper: log in via API and set token in localStorage (faster). */
async function loginViaAPI(
  page: Page,
  username: string,
  role: "biker" | "planner"
) {
  const res = await page.request.post(`${API_BASE}/auth/login/`, {
    data: { username, role },
  });
  const { token } = await res.json();
  await page.goto("/");
  await page.evaluate((t) => localStorage.setItem("auth-token", t), token);
  await page.reload();
  await expect(page.locator("h1", { hasText: "LastMile" })).toBeVisible({
    timeout: 15_000,
  });
  await page.waitForLoadState("networkidle");
}

/**
 * Helper: run the planning wizard (upload -> geocode -> fix addresses) until the
 * optimize step, where the stop list and map are shown.
 */
async function uploadTestFile(page: Page, fileName: string | string[]) {
  const names = Array.isArray(fileName) ? fileName : [fileName];
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(
    names.map((n) => path.resolve(__dirname, "test-data", n))
  );
  await page.getByRole("button", { name: /Upload & continue/ }).click();

  // Step 2 geocodes automatically; Next unlocks once nothing is pending.
  const footer = page.locator(".wizard-footer");
  const toFix = footer.getByRole("button", { name: /(Fix|Review) addresses/ });
  await expect(toFix).toBeEnabled({ timeout: 90_000 });
  await toFix.click();

  // Step 3: continue (with or without unresolved addresses).
  await footer.getByRole("button", { name: /^Continue/ }).click();

  // Step 4: keep every postal code.
  await footer.getByRole("button", { name: /^Continue/ }).click();
}

/** Helper: clean up test user via API */
async function logoutViaUI(page: Page) {
  const signOutBtn = page.locator('[title="Sign out"]');
  if (await signOutBtn.isVisible()) {
    await signOutBtn.click();
  }
}

/** Paths to test data files */
const TEST_FILES = {
  geocoded: path.resolve(__dirname, "test-data", "geocoded_stops.csv"),
  needsGeocoding: path.resolve(__dirname, "test-data", "needs_geocoding.csv"),
};

export {
  base as test,
  expect,
  loginViaUI,
  loginViaAPI,
  uploadTestFile,
  logoutViaUI,
  TEST_FILES,
  API_BASE,
};
