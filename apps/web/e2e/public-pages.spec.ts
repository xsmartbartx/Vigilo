import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

test.skip(
  !process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || !process.env.CLERK_SECRET_KEY,
  "needs Clerk dev keys (see playwright.config.ts)",
);

async function guard(page: Page) {
  const problems: string[] = [];
  page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));
  page.on("response", (r) => {
    if (r.status() >= 500) problems.push(`${r.status()} ${r.url()}`);
  });
  return problems;
}

const NEXORA = (process.env.NEXT_PUBLIC_NEXORA_URL ?? "https://onenexora.com").replace(/\/$/, "");

test("F01-H1 pricing shows Vigilo's plans only and toggles annual prices", async ({ page }) => {
  const problems = await guard(page);
  await page.goto("/pricing");
  await expect(page.getByRole("heading", { level: 1, name: "Vigilo pricing" })).toBeVisible();
  await expect(page.getByText("$29/mo")).toBeVisible();
  await page.getByRole("radio", { name: "Annual" }).click();
  await expect(page.getByText("$290/yr")).toBeVisible();
  // A visitor can start buying: "Get Pro" signs them in and returns them to the billing page.
  await expect(page.getByRole("link", { name: "Get Pro" })).toHaveAttribute(
    "href",
    "/sign-in?redirect_url=%2Fdashboard%2Fbilling",
  );
  for (const other of ["Sentinel", "CSPM", "Gateway", "NeuraWall"]) {
    await expect(page.getByRole("heading", { name: other })).toHaveCount(0);
  }
  expect(problems).toEqual([]);
});

test("F01-H2 the platform catalogue lives on the Nexora site: old product URLs redirect there", async ({
  request,
}) => {
  for (const [from, to, status] of [
    ["/products", `${NEXORA}/products`, 307],
    ["/products/sentinel", `${NEXORA}/products/sentinel`, 307],
    ["/products/vigilo", "/", 308],
  ] as const) {
    const res = await request.get(from, { maxRedirects: 0 });
    expect(res.status(), from).toBe(status);
    expect(res.headers()["location"], from).toBe(to);
  }
});

test("F01-E1 no horizontal scroll at this viewport", async ({ page }) => {
  await guard(page);
  for (const path of ["/", "/pricing"]) {
    await page.goto(path);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow, path).toBeLessThanOrEqual(0);
  }
});

test("F01-E2 keyboard can reach and flip the billing interval", async ({ page }) => {
  await guard(page);
  await page.goto("/pricing");
  const annual = page.getByRole("radio", { name: "Annual" });
  await annual.focus();
  await page.keyboard.press("Enter");
  await expect(annual).toHaveAttribute("aria-checked", "true");
});

test("F01-H4 the home page is Vigilo's own: a Nexora bar, product navigation, the scan form", async ({
  page,
}) => {
  const problems = await guard(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("shows only what it can prove");
  // The company bar sends people back to the Nexora site.
  await expect(page.getByRole("link", { name: "NEXORA", exact: true })).toHaveAttribute("href", NEXORA);
  await expect(page.getByRole("link", { name: "All products" })).toHaveAttribute("href", `${NEXORA}/products`);
  // The product bar has Vigilo's own sections and a way in.
  const nav = page.getByRole("navigation", { name: "Vigilo sections" });
  for (const label of ["How it works", "Features", "Pricing", "FAQ"]) {
    await expect(nav.getByRole("link", { name: label })).toBeVisible();
  }
  await expect(page.getByRole("link", { name: "Scan free" })).toHaveAttribute("href", "/#scan");
  await expect(page.getByRole("button", { name: "Scan it" })).toBeVisible();
  // It is not the platform's home any more.
  await expect(page.getByText("One account for the tools")).toHaveCount(0);
  expect(problems).toEqual([]);
});

test("F01-H6 the home page keeps the scan form", async ({ page }) => {
  await guard(page);
  await page.goto("/");
  await expect(page.getByLabel(/URL|site/i).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Scan it" })).toBeVisible();
});

test("F01-N1 an unknown page is a 404", async ({ page }) => {
  await guard(page);
  const missing = await page.goto("/does-not-exist");
  expect(missing?.status()).toBe(404);
});

for (const path of ["/", "/pricing"]) {
  test(`A11Y axe scan ${path}`, async ({ page }) => {
    await guard(page);
    await page.goto(path);
    const results = await new AxeBuilder({ page } as ConstructorParameters<typeof AxeBuilder>[0]).withTags(["wcag2a", "wcag2aa"]).analyze();
    expect(results.violations.map((v) => `${v.id}: ${v.help}`)).toEqual([]);
  });
}

test("F01-H9 trust page lists practices and is accessible", async ({ page }) => {
  const problems = await guard(page);
  await page.goto("/trust");
  await expect(page.getByRole("heading", { level: 1, name: "Trust and security" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "Audit trail" })).toBeVisible();
  const results = await new AxeBuilder({ page } as ConstructorParameters<typeof AxeBuilder>[0]).withTags(["wcag2a", "wcag2aa"]).analyze();
  expect(results.violations).toEqual([]);
  await expect(page.getByRole("link", { name: "Trust and security" })).toBeVisible();
  expect(problems).toEqual([]);
});

test("F01-H10 the scan form accepts a bare domain and explains a non-address", async ({ page }) => {
  let sent: string | null = null;
  // The request is captured and dropped: nothing is submitted to the API.
  await page.route("**/v1/scans**", async (route) => {
    sent = route.request().postData();
    await route.abort();
  });
  await page.goto("/");
  const url = page.getByLabel("Site URL").first();
  const email = page.getByLabel(/^Email/).first();
  const submit = page.getByRole("button", { name: "Scan it" }).first();

  await url.fill("not an address");
  await email.fill("review@example.com");
  await submit.click();
  await expect(page.getByText("Enter a website address")).toBeVisible();
  expect(sent).toBeNull();

  await url.fill("example.com/path");
  await submit.click();
  await expect.poll(() => sent).toContain("https://example.com/path");
});

test("F01-H11 the sign-up page links the terms and the privacy policy", async ({ page }) => {
  await page.goto("/sign-up");
  await expect(page.getByRole("link", { name: "Terms of Service" })).toHaveAttribute("href", "/terms");
  await expect(page.getByRole("link", { name: "Privacy Policy" })).toHaveAttribute("href", "/privacy");
});
