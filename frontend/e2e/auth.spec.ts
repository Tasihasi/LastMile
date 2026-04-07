import { test, expect, loginViaUI, logoutViaUI } from "./fixtures";

test.describe("Authentication", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("shows login screen when not authenticated", async ({ page }) => {
    await expect(page.locator("h1", { hasText: "LastMile" })).toBeVisible();
    await expect(
      page.getByText("Sign in to plan and view delivery routes")
    ).toBeVisible();
    await expect(page.getByLabel("Username")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Biker" })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Planner" })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Sign In" })
    ).toBeVisible();
  });

  test("requires username to sign in", async ({ page }) => {
    await page.getByRole("button", { name: "Sign In" }).click();
    await expect(page.getByText("Please enter a username")).toBeVisible();
  });

  test("login as biker shows session list", async ({ page }) => {
    await loginViaUI(page, "E2EBiker", "biker");
    // Biker sees session list (Recent Routes heading or empty state)
    await expect(
      page.getByText(/Recent Routes|No routes yet/)
    ).toBeVisible();
    // Username shown in header
    await expect(page.locator(".user-badge-name")).toHaveText("E2EBiker");
  });

  test("login as planner shows dashboard", async ({ page }) => {
    await loginViaUI(page, "E2EPlanner", "planner");
    // Planner sees the dashboard
    await expect(page.getByText("Route Management")).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.locator(".user-badge-name")).toHaveText("E2EPlanner");
  });

  test("logout returns to login screen", async ({ page }) => {
    await loginViaUI(page, "E2ELogout", "biker");
    await expect(page.locator(".user-badge-name")).toHaveText("E2ELogout");
    await logoutViaUI(page);
    await expect(
      page.getByText("Sign in to plan and view delivery routes")
    ).toBeVisible();
  });

  test("role selection highlights active role", async ({ page }) => {
    // Biker is default
    const bikerBtn = page.getByRole("button", { name: "Biker" });
    const plannerBtn = page.getByRole("button", { name: "Planner" });
    await expect(bikerBtn).toHaveClass(/role-option--active/);
    await expect(plannerBtn).not.toHaveClass(/role-option--active/);

    // Switch to planner
    await plannerBtn.click();
    await expect(plannerBtn).toHaveClass(/role-option--active/);
    await expect(bikerBtn).not.toHaveClass(/role-option--active/);
  });

  test("token persists across page reload", async ({ page }) => {
    await loginViaUI(page, "E2EPersist", "biker");
    await expect(page.locator(".user-badge-name")).toHaveText("E2EPersist");
    await page.reload();
    // Still logged in after reload
    await expect(page.locator(".user-badge-name")).toHaveText("E2EPersist");
  });
});
