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

/** Helper: upload a file by setting it on the hidden input. */
async function uploadTestFile(page: Page, fileName: string) {
  const filePath = path.resolve(__dirname, "test-data", fileName);
  const fileInput = page.locator('input[type="file"]');
  await fileInput.setInputFiles(filePath);
}

/** Helper: open the user menu dropdown and click Sign out. */
async function logoutViaUI(page: Page) {
  // The username badge in the header now opens an account dropdown rather
  // than logging out instantly. Click it, then click the Sign out menu item.
  const userBadge = page.locator(".user-badge");
  if (!(await userBadge.isVisible())) return;
  await userBadge.click();
  const signOutItem = page.locator('.user-menu-item[title="Sign out"]');
  await signOutItem.click();
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
