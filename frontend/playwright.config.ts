import { defineConfig, devices } from "@playwright/test";

const CI = !!process.env.CI;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: CI,
  retries: CI ? 1 : 0,
  workers: 1,
  reporter: CI ? "github" : "html",
  timeout: 60_000,
  expect: { timeout: 10_000 },

  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  webServer: [
    {
      command:
        "cd ../backend && python manage.py migrate --run-syncdb > /dev/null 2>&1 && python manage.py seed_test_data && python manage.py runserver 8000 --noreload",
      port: 8000,
      reuseExistingServer: !CI,
      timeout: 30_000,
      env: {
        E2E_MOCK: "true",
        ORS_API_KEY: "e2e-mock-key",
        DEBUG: "True",
      },
    },
    {
      command: "npx vite --port 5173",
      port: 5173,
      reuseExistingServer: !CI,
      timeout: 15_000,
    },
  ],
});
