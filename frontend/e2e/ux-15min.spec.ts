import { test, expect, loginViaAPI } from "./fixtures";
import type { Page } from "@playwright/test";

/**
 * UX ruling: the planner's whole working day (login -> upload -> geocode -> fix -> postal
 * codes -> bikers -> review -> optimize) must take no more than 15 minutes.
 *
 * Two clocks are reported per stage:
 *  - system: measured wall time of this run (E2E_MOCK, so geocoding is instant);
 *  - human : a keystroke-level model (KLM) estimate of what a person needs on that screen
 *            (reading, pointing, clicking, typing), plus the REAL geocoder wait
 *            (GEOCODE_SECONDS_PER_STOP, the wizard copy promises "about a second per stop").
 * The ruling is checked against system + human + real geocoder wait.
 */

const BUDGET_S = 15 * 60;
const GEOCODE_SECONDS_PER_STOP = 1; // see GeocodeStep copy
const HUMAN = { click: 2.0, read: 4.0, perChar: 0.25, decide: 5.0 }; // seconds

// A realistic day: 231 stops over zips of districts V-IX, one oversized zip (1054).
const DAY: Record<string, [number, number, number]> = {
  "1051": [47.499, 19.05, 10],
  "1052": [47.495, 19.053, 8],
  "1054": [47.504, 19.048, 56],
  "1055": [47.513, 19.046, 14],
  "1061": [47.504, 19.062, 20],
  "1065": [47.506, 19.059, 18],
  "1072": [47.5, 19.069, 25],
  "1073": [47.504, 19.072, 22],
  "1081": [47.495, 19.08, 20],
  "1085": [47.49, 19.069, 18],
  "1086": [47.49, 19.09, 20],
};

/** `failures` stops are written without a city (the mock geocoder misses them, like a real typo). */
function dayCsv(failures = 0): { csv: string; total: number } {
  const rows = [failures ? "name,address" : "name,address,lat,lng"];
  let n = 0;
  for (const [zip, [lat, lng, count]] of Object.entries(DAY)) {
    for (let i = 0; i < count; i++) {
      n++;
      const jitter = (k: number) => ((((n * k) % 17) - 8) / 8) * 0.004;
      if (failures) {
        rows.push(`Stop ${n},${zip} ${n <= failures ? "nocity" : "Budapest"} Teszt utca ${i + 1}`);
      } else {
        rows.push(
          `Stop ${n},${zip} Budapest Teszt utca ${i + 1},${(lat + jitter(7)).toFixed(6)},${(lng + jitter(11)).toFixed(6)}`
        );
      }
    }
  }
  return { csv: rows.join("\n"), total: n };
}

type Stage = { name: string; system: number; human: number; clicks: number };

test.describe("UX ruling: whole planner day <= 15 minutes", () => {
  test.setTimeout(240_000);
  test.use({ viewport: { width: 1366, height: 768 } }); // common laptop

  const FIX_SECONDS_PER_ADDRESS = 25; // find, retype, search, re-check one address by hand

  async function runDay(page: Page, opts: { failures?: number; byTime?: boolean }) {
    const failures = opts.failures ?? 0;
    const stages: Stage[] = [];
    let clicks = 0;
    let t0 = Date.now();

    const stage = (name: string, human: number, c: number) => {
      stages.push({ name, system: (Date.now() - t0) / 1000, human, clicks: c });
      clicks += c;
      t0 = Date.now();
    };
    const inViewport = async (page: Page, sel: ReturnType<Page["locator"]>, what: string) => {
      const box = await sel.boundingBox();
      expect(box, `${what} must exist`).not.toBeNull();
      expect(box!.y + box!.height, `${what} must be visible without scrolling at 1366x768`).toBeLessThanOrEqual(768);
    };

    const { csv, total } = dayCsv(failures);

    // 1. Sign in ---------------------------------------------------------
    await loginViaAPI(page, "Planner", "planner");
    // KLM: type name (7 chars), pick role, press Sign In.
    stage("Sign in", HUMAN.read + 7 * HUMAN.perChar + 2 * HUMAN.click, 3);

    // 2. Start a route ---------------------------------------------------
    await page.getByRole("button", { name: /New Route|Upload/ }).first().click();
    await expect(page.getByRole("heading", { name: /Upload your delivery files/ })).toBeVisible();
    stage("Open new route", HUMAN.read + HUMAN.click, 1);

    // 3. Upload ----------------------------------------------------------
    await page.locator('input[type="file"]').setInputFiles({
      name: "monday.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(csv),
    });
    await expect(page.locator(".wizard-file")).toHaveCount(1);
    const footer = page.locator(".wizard-footer");
    await inViewport(page, footer.getByRole("button", { name: /Upload & continue/ }), "Upload & continue");
    await footer.getByRole("button", { name: /Upload & continue/ }).click();
    // Picking a file in the OS dialog ~8 s, click Upload.
    stage("Upload file", 8 + HUMAN.click, 2);

    // 4. Geocode (auto) --------------------------------------------------
    const toFix = footer.getByRole("button", { name: /(Fix|Review) addresses/ });
    await expect(toFix).toBeEnabled({ timeout: 90_000 });
    await expect(page.locator(".wizard-stat strong").first()).toHaveText(String(total));
    // The "Not found" counter lives on this step; the next step only lists the misses.
    if (failures > 0) await expect(page.locator(".wizard-stat--bad strong")).toHaveText(String(failures));
    await inViewport(page, toFix, "Review addresses");
    const geocodeWait = total * GEOCODE_SECONDS_PER_STOP;
    await toFix.click();
    stage("Geocode (real wait modelled)", geocodeWait + HUMAN.read + HUMAN.click, 1);

    // 5. Fix addresses ---------------------------------------------------
    if (failures === 0) {
      await expect(page.getByText("Every address was found")).toBeVisible();
      await footer.getByRole("button", { name: /^Continue/ }).click();
      stage("Fix addresses (nothing to fix)", HUMAN.read + HUMAN.click, 1);
    } else {
      const retry = page.getByRole("button", { name: new RegExp(`Retry all ${failures}`) });
      await inViewport(page, retry, "Retry all");
      await retry.click();
      await expect(page.locator(".fix-row--ok")).toHaveCount(failures, { timeout: 60_000 });
      await footer.getByRole("button", { name: /^Continue/ }).click();
      // Without the bulk button every row would cost FIX_SECONDS_PER_ADDRESS by hand.
      stage(`Fix ${failures} addresses (bulk retry)`, HUMAN.read * 2 + HUMAN.click * 2, 2);
    }

    // 6. Postal codes ----------------------------------------------------
    await expect(page.locator(".postal-group")).toHaveCount(Object.keys(DAY).length);
    await expect(page.getByText(`${total} of ${total} stops included`)).toBeVisible();
    await inViewport(page, footer.getByRole("button", { name: /^Continue/ }), "Continue (postal codes)");
    await footer.getByRole("button", { name: /^Continue/ }).click();
    stage("Postal codes (accept all)", HUMAN.read * 2 + HUMAN.click, 1);

    // 7. Bikers ----------------------------------------------------------
    const dialog = page.getByRole("dialog", { name: "Split route planner" });
    await expect(dialog).toBeVisible();
    const submit = dialog.getByRole("button", { name: /^Split (between|automatically)/ });
    await inViewport(page, submit, "Split button");
    if (opts.byTime) {
      await dialog.getByLabel(/Plan by available time/).check();
      await expect(dialog.getByLabel(/^Shift hours for/).first()).toBeVisible();
    }
    if (!opts.byTime) await expect(dialog.getByText(new RegExp(`${total}/${total} stops planned`))).toBeVisible();
    await submit.click();
    stage("Choose bikers & split", HUMAN.decide * 2 + HUMAN.click * (opts.byTime ? 3 : 2), opts.byTime ? 3 : 2);

    // 8. Review ----------------------------------------------------------
    await expect(page.locator(".cluster-review")).toBeVisible({ timeout: 60_000 });
    const routes = await page.locator(".cluster-route-card, .cluster-route").count();
    expect(routes, "review shows at least one route per biker").toBeGreaterThan(0);
    await expect(page.getByTestId("zip-conflict-banner")).toHaveCount(0);
    stage("Review split on map", HUMAN.read * 3 + HUMAN.decide * 3, 0);

    // 9. Optimize all ----------------------------------------------------
    const optimizeAll = page.getByRole("button", { name: /Optimize All/ });
    if (await optimizeAll.isVisible()) {
      await inViewport(page, optimizeAll, "Optimize All");
      await optimizeAll.click();
      await expect(optimizeAll).toBeHidden({ timeout: 120_000 });
    }
    stage("Optimize all routes", HUMAN.click + HUMAN.read, 1);

    // ---- Ruling --------------------------------------------------------
    const sys = stages.reduce((a, s) => a + s.system, 0);
    const human = stages.reduce((a, s) => a + s.human, 0);
    const lines = stages.map(
      (s) => `  ${s.name.padEnd(36)} system ${s.system.toFixed(1).padStart(6)}s  human ${s.human.toFixed(1).padStart(6)}s  clicks ${s.clicks}`
    );
    // eslint-disable-next-line no-console
    console.log(
      `\nUX timing, ${total} stops, ${Object.keys(DAY).length} zips\n${lines.join("\n")}\n  TOTAL system ${sys.toFixed(1)}s + human ${human.toFixed(1)}s = ${(sys + human).toFixed(1)}s of ${BUDGET_S}s, ${clicks} clicks\n`
    );
    expect(sys + human, "whole flow must fit in 15 minutes").toBeLessThanOrEqual(BUDGET_S);
    expect(clicks, "click count stays low").toBeLessThanOrEqual(15);
    return sys + human;
  }

  test("login to optimized routes", async ({ page }) => {
    await runDay(page, {});
  });

  test("20 mistyped addresses are fixed with one click and still fit the budget", async ({ page }) => {
    const total = await runDay(page, { failures: 20 });
    // Worst case without the bulk button, for the record: 20 fixes by hand.
    expect(total + 20 * FIX_SECONDS_PER_ADDRESS).toBeLessThanOrEqual(BUDGET_S);
  });

  test("planning by available time sends shift windows and reaches the review", async ({ page }) => {
    const sent: unknown[] = [];
    page.on("request", (r) => {
      if (/\/cluster\/$/.test(r.url()) && r.method() === "POST") sent.push(r.postDataJSON());
    });
    await runDay(page, { byTime: true });
    const body = sent[0] as { assignments: { window_minutes: number; zip: unknown; district: unknown }[] };
    expect(body.assignments.length).toBeGreaterThan(0);
    for (const a of body.assignments) {
      expect(a.window_minutes).toBe(420);
      expect(a.zip ?? null).toBeNull();
      expect(a.district ?? null).toBeNull();
    }
  });
});
