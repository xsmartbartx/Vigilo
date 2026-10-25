import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import {
  E2E_USER_EMAIL,
  expectNoProblems,
  signIn,
  skipUnlessSignedInTestsConfigured,
  watch,
} from "./auth";

skipUnlessSignedInTestsConfigured();

// The whole scan pipeline: needs the API, a scanner worker (Redis) and outbound
// network access to https://example.com. Desktop only; one scan shared by the
// specs below.
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ browserName }, testInfo) => {
  void browserName;
  test.skip(testInfo.project.name !== "desktop", "scan pipeline: desktop only");
});

let reportUrl = "";

test("S-SCAN-1 a signed-in owner scans a site and reaches a finished report", async ({ page }) => {
  test.setTimeout(180_000);
  await signIn(page);
  await page.goto("/");
  await page.getByLabel("Site URL").fill("https://example.com");
  await page.getByLabel(/email/i).fill(E2E_USER_EMAIL!);
  await page.getByRole("button", { name: "Scan it" }).click();
  await expect(page).toHaveURL(/\/reports\/[0-9a-f-]{36}/);
  reportUrl = page.url();

  // The report is built by the worker. The page tells the visitor and refreshes by itself:
  // no reload here, that is the behaviour under test.
  await expect(page.getByText(/\/ 100/)).toBeVisible({ timeout: 150_000 });
  await expect(page.getByText(/example\.com/).first()).toBeVisible();
});

test("S-SCAN-2 the report is readable: score, grouped findings, fixes, skipped checks", async ({ page }) => {
  test.skip(!reportUrl, "needs S-SCAN-1");
  const problems = watch(page);
  await signIn(page);
  await page.goto(reportUrl);
  await expect(page.getByText(/\/ 100/)).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: /Critical|High|Medium|Low|Info/ }).first()).toBeVisible();
  await expect(page.getByText("How to fix this").first()).toBeVisible();
  // more than three open findings: the "fix these first" summary leads, with links to the cards
  const open = await page.getByRole("button", { name: "Accept risk" }).count();
  if (open > 3) {
    const fixFirst = page.getByRole("region", { name: "Fix these 3 first" });
    await expect(fixFirst).toBeVisible();
    await expect(fixFirst.getByRole("link")).toHaveCount(3);
    const href = await fixFirst.getByRole("link").first().getAttribute("href");
    await expect(page.locator(href!)).toBeVisible(); // the link lands on a real card
  }
  await expectNoProblems(problems);
  const results = await new AxeBuilder({ page } as ConstructorParameters<typeof AxeBuilder>[0])
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.help} (${v.nodes.map((n) => n.target.join(" ")).join(" | ")})`)).toEqual([]);
});

test("S-SCAN-3 an owner can accept a risk with a reason; it moves to accepted risks and is audited", async ({ page }) => {
  test.skip(!reportUrl, "needs S-SCAN-1");
  await signIn(page);
  await page.goto(reportUrl);
  const accept = page.getByRole("button", { name: "Accept risk" }).first();
  await expect(accept).toBeVisible(); // owner-only control
  const before = await page.getByRole("button", { name: "Accept risk" }).count();
  await accept.click();
  const confirm = page.getByRole("button", { name: "Confirm" });
  await expect(confirm).toBeDisabled(); // a reason is required
  await page.getByPlaceholder(/Why is this accepted/).fill("e2e: known and tolerated");
  await confirm.click();
  await expect(page.getByRole("button", { name: "Accept risk" })).toHaveCount(before - 1);
  // The accepted-risks list is collapsed by default; the owner sees who-said-what: the reason.
  await page.getByText(/^Accepted risks \(1\)/).click();
  await expect(page.getByText("e2e: known and tolerated")).toBeVisible();

  // and can reopen it: the finding comes back to the open list
  await page.getByRole("button", { name: "Restore" }).click();
  await expect(page.getByRole("button", { name: "Accept risk" })).toHaveCount(before);
  await expect(page.getByText(/^Accepted risks/)).toHaveCount(0);

  // accept it again so the audit log has an acceptance to find
  await page.getByRole("button", { name: "Accept risk" }).first().click();
  await page.getByPlaceholder(/Why is this accepted/).fill("e2e: second time");
  await page.getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByRole("button", { name: "Accept risk" })).toHaveCount(before - 1);

  await page.goto("/console/audit");
  await expect(page.getByRole("table")).toContainText("Accepted a risk");
});

test("S-SCAN-4 a signed-out visitor sees the same report without owner controls", async ({ browser }) => {
  test.skip(!reportUrl, "needs S-SCAN-1");
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(reportUrl);
  await expect(page.getByText(/\/ 100/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Accept risk" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /export|pdf/i })).toHaveCount(0);
  await context.close();
});
