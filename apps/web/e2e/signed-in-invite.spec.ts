import { expect, test } from "@playwright/test";
import { expectNoProblems, signIn, skipUnlessSignedInTestsConfigured, watch } from "./auth";

skipUnlessSignedInTestsConfigured();

// Accepting an invitation as a second, real person. It needs a second user that
// already exists in the Clerk development instance (create one in the Clerk
// dashboard, sign-in by email only) and its address in E2E_SECOND_USER_EMAIL. Without
// it the spec is skipped, so CI and local runs without a second user are unaffected.
const SECOND = process.env.E2E_SECOND_USER_EMAIL;
test.skip(!SECOND, "needs E2E_SECOND_USER_EMAIL: a second user in the Clerk dev instance");
test.beforeEach(async ({ browserName }, testInfo) => {
  void browserName;
  test.skip(testInfo.project.name !== "desktop", "mutating: desktop only");
});

const RUN = Date.now().toString(36);
const SLUG = `e2e-invite-${RUN}`;
const NAME = `E2E invite ${RUN}`;
const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:3000";

test("S-INVITE-1 an invitation works once, only for the invited person", async ({ page, browser }) => {
  const problems = watch(page);

  // The owner creates an organisation and invites the second user. No email provider is
  // configured in the test stack, so the one-time link is shown on the page.
  await signIn(page);
  await page.goto("/console/new-org");
  await page.getByLabel("Name").fill(NAME);
  await page.getByLabel("Address").fill(SLUG);
  await page.getByRole("button", { name: "Create organisation" }).click();
  await expect(page).toHaveURL(/\/console$/);
  await page.goto("/console/members");
  await page.getByLabel("Email address").fill(SECOND!);
  await page.getByRole("button", { name: "Create invitation" }).click();
  const link = await page.getByLabel("Invitation link").inputValue();
  expect(link).toMatch(/\/invite\/.+/);

  // The owner is the wrong person for this link: it is for the other address only.
  await page.goto(new URL(link).pathname);
  await page.getByRole("button", { name: "Accept invitation" }).click();
  await expect(page.getByRole("alert").filter({ hasText: /./ }).first()).toBeVisible();

  // The invited person, in their own browser session, accepts it.
  const ctx = await browser.newContext({ baseURL: BASE_URL });
  const second = await ctx.newPage();
  const secondProblems = watch(second);
  await signIn(second, SECOND!);
  await second.goto(new URL(link).pathname);
  await second.getByRole("button", { name: "Accept invitation" }).click();
  await expect(second).toHaveURL(/\/console/);
  await expect(second.locator("#org-switcher option", { hasText: NAME })).toHaveCount(1);

  // The owner now sees them as a member.
  await page.goto("/console/members");
  await expect(page.getByRole("table")).toContainText(SECOND!);

  // It was one-time: the same link a second time does not add them again.
  await second.goto(new URL(link).pathname);
  await second.getByRole("button", { name: "Accept invitation" }).click();
  await expect(second.getByRole("alert").filter({ hasText: /./ }).first()).toBeVisible();

  await expectNoProblems(problems);
  await expectNoProblems(secondProblems);
  await ctx.close();
});
