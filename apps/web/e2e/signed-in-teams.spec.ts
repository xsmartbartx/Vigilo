import { expect, test, type Page } from "@playwright/test";
import { addMember, sql } from "./db";
import { expectNoProblems, signIn, skipUnlessSignedInTestsConfigured, watch } from "./auth";

skipUnlessSignedInTestsConfigured();

// Organisations, the switcher, roles and the launcher in one browser session.
// Desktop only (it mutates); needs the e2e database (scripts/e2e-up.sh).
test.describe.configure({ mode: "serial" });
test.beforeEach(async ({ browserName }, testInfo) => {
  void browserName;
  test.skip(testInfo.project.name !== "desktop", "mutating: desktop only");
});

// Choose an organisation in the switcher and wait until the server has applied it.
// Selecting an option changes the control at once, in the browser; what matters is
// the server action's response (it sets the cookie), so wait for that, not the control.
async function switchTo(page: Page, name: string) {
  await page.getByLabel("Organisation").selectOption({ label: name });
  await Promise.all([
    page.waitForResponse((r) => r.request().method() === "POST" && r.status() < 400),
    page.getByRole("button", { name: "Switch" }).click(),
  ]);
  await page.waitForLoadState("networkidle");
  await expect(page.locator("#org-switcher option:checked")).toHaveText(name);
}

const RUN = Date.now().toString(36);
const SLUG = `e2e-team-${RUN}`;
const NAME = `E2E crew ${RUN}`;
const MATE = `mate-${RUN}@example.test`;

const NEXORA = (process.env.NEXT_PUBLIC_NEXORA_URL ?? "https://onenexora.com").replace(/\/$/, "");

test("S-TEAM-1 create an organisation, then add a second member to it", async ({ page }) => {
  await signIn(page);
  await page.goto("/console/new-org");
  await page.getByLabel("Name").fill(NAME);
  await page.getByLabel("Address").fill(SLUG);
  await page.getByRole("button", { name: "Create organisation" }).click();
  await expect(page).toHaveURL(/\/console$/);
  await addMember(SLUG, MATE, "member");
  await page.goto("/console/members");
  await expect(page.getByRole("table")).toContainText(MATE);
});

test("S-TEAM-2 an admin changes a member's role and the audit log says so", async ({ page }) => {
  const problems = watch(page);
  await signIn(page);
  await page.goto("/console/members");
  await switchTo(page, NAME);
  await page.goto("/console/members");
  const row = page.getByRole("row", { name: new RegExp(MATE) });
  await expect(row.getByLabel(`Role for ${MATE}`)).toHaveValue("member");
  await row.getByLabel(`Role for ${MATE}`).selectOption("admin");
  await row.getByRole("button", { name: "Save" }).click();
  await expect(page.getByRole("row", { name: new RegExp(MATE) }).getByLabel(`Role for ${MATE}`)).toHaveValue("admin");

  await page.goto("/console/audit");
  await expect(page.getByRole("table")).toContainText(`Changed ${MATE}'s role from member to admin`);
  await expectNoProblems(problems);
});

test("S-TEAM-3 removing a member asks for confirmation, then they are gone", async ({ page }) => {
  await signIn(page);
  await page.goto("/console/members");
  await switchTo(page, NAME);
  await page.goto("/console/members");
  const row = page.getByRole("row", { name: new RegExp(MATE) });
  await row.getByText("Remove", { exact: true }).click(); // opens the confirmation
  await expect(row.getByText(/loses access to this organisation at once/)).toBeVisible();
  await row.getByRole("button", { name: `Remove ${MATE}` }).click();
  await expect(page.getByRole("table")).not.toContainText(MATE);
  expect(await sql(`select count(*) from memberships m join accounts a on a.id = m.account_id where a.email = '${MATE}'`)).toBe("0");

  await page.goto("/console/audit");
  await expect(page.getByRole("table")).toContainText(`Removed ${MATE} from the organisation`);
});

test("S-TEAM-4 the switcher keeps each organisation's targets apart", async ({ page }) => {
  await signIn(page);
  const origin = `https://crew-${RUN}.example.com`;

  await page.goto("/console");
  await switchTo(page, NAME);
  await page.goto("/dashboard/targets");
  await page.getByPlaceholder(/https?:\/\//).first().fill(origin);
  await page.getByRole("button", { name: /^add/i }).click();
  await expect(page.getByText(origin)).toBeVisible();

  // back in the personal workspace the crew's target is not there
  await switchTo(page, "Personal workspace");
  await page.goto("/dashboard/targets");
  await expect(page.getByText(origin)).toHaveCount(0);

  // and it is still there for the crew
  await switchTo(page, NAME);
  await page.goto("/dashboard/targets");
  await expect(page.getByText(origin)).toBeVisible();
});

test("S-TEAM-5 the launcher shows Vigilo as enabled and the other four as not open yet", async ({ page }) => {
  await signIn(page);
  await page.goto("/console");
  await switchTo(page, NAME);
  await page.goto("/console");

  // Vigilo is on for every organisation from the start; the engines of the other
  // four are separate projects, so there is nothing to enable.
  await expect(page.getByText("Enabled", { exact: true })).toHaveCount(1);
  await expect(page.getByText("Coming soon", { exact: true })).toHaveCount(4);
  await expect(page.getByRole("button", { name: /^Enable / })).toHaveCount(0);
  await expect(page.getByText("Not open yet.")).toHaveCount(4);

  // "What is planned" goes to that product's page on the Nexora site (this site is
  // Vigilo's own, so it does not carry the other products' pages).
  await expect(page.getByRole("link", { name: "What is planned" }).first()).toHaveAttribute(
    "href",
    new RegExp(`^${NEXORA.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}/products/(sentinel|cspm|gateway|neurawall)$`),
  );
});

test("S-TEAM-6 the owner hands a team organisation to another member", async ({ page }) => {
  const slug = `e2e-own-${RUN}`;
  const name = `E2E handover ${RUN}`;
  const heir = `heir-${RUN}@example.test`;
  await signIn(page);
  await page.goto("/console/new-org");
  await page.getByLabel("Name").fill(name);
  await page.getByLabel("Address").fill(slug);
  await page.getByRole("button", { name: "Create organisation" }).click();
  await expect(page).toHaveURL(/\/console$/);
  await addMember(slug, heir, "admin");
  await page.goto("/console/members");

  const row = page.getByRole("row", { name: new RegExp(heir) });
  await row.getByText("Make owner", { exact: true }).click();
  await expect(row.getByText(/becomes the owner of/)).toBeVisible();

  // a wrong confirmation is refused and nothing changes
  await row.getByLabel(/Type .* to confirm/).fill("not-the-address");
  await row.getByRole("button", { name: `Hand over to ${heir}` }).click();
  await expect(page.getByRole("alert").filter({ hasText: /not this organisation/ })).toBeVisible();
  expect(await sql(`select role from memberships m join accounts a on a.id = m.account_id where a.email = '${heir}'`)).toBe("admin");

  // the right one hands it over: I am an admin now, they own it, and the control is gone
  await row.getByLabel(/Type .* to confirm/).fill(slug);
  await row.getByRole("button", { name: `Hand over to ${heir}` }).click();
  await expect(page.getByRole("row", { name: new RegExp(heir) })).toContainText("owner");
  await expect(page.getByText("Make owner", { exact: true })).toHaveCount(0);
  expect(await sql(`select count(*) from memberships m join organizations o on o.id = m.org_id where o.slug = '${slug}' and m.role = 'owner'`)).toBe("1");
  expect(await sql(`select a.email from organizations o join accounts a on a.id = o.created_by where o.slug = '${slug}'`)).toBe(heir);

  await page.goto("/console/audit");
  await expect(page.getByRole("table")).toContainText(`Handed the organisation to ${heir}`);
});
