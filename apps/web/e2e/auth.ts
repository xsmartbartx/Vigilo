import { clerk, setupClerkTestingToken } from "@clerk/testing/playwright";
import { expect, test, type Page } from "@playwright/test";

export const E2E_USER_EMAIL = process.env.E2E_USER_EMAIL;

export function skipUnlessSignedInTestsConfigured() {
  test.skip(
    !process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || !process.env.CLERK_SECRET_KEY || !E2E_USER_EMAIL,
    "needs Clerk dev keys and E2E_USER_EMAIL (see playwright.config.ts)",
  );
}

export async function signIn(page: Page, email: string = E2E_USER_EMAIL!) {
  await setupClerkTestingToken({ page });
  // "load" waits on every third-party asset; one stalled request then fails the
  // whole test. Clerk's own helper waits for Clerk to be ready.
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await clerk.signIn({ page, emailAddress: email });
}

// Collects what a person would never see but a bug would cause.
export function watch(page: Page) {
  const problems: string[] = [];
  page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));
  page.on("response", (r) => {
    if (r.status() >= 500) problems.push(`${r.status()} ${r.url()}`);
  });
  page.on("console", (m) => {
    // The Clerk dev banner and HMR chatter are not ours; real errors are.
    if (m.type() === "error" && !/clerk|hmr|websocket|favicon/i.test(m.text())) {
      problems.push(`console: ${m.text().slice(0, 200)}`);
    }
  });
  return problems;
}

export async function expectNoProblems(problems: string[]) {
  expect(problems).toEqual([]);
}
