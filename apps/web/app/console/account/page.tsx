import Link from "next/link";
import { api } from "../../../lib/api";
import { DeleteAccountForm } from "../../../components/console/DeleteAccountForm";
import { sessionToken } from "../../../lib/nexora/data";
import { Card } from "../../../components/ui";

export const metadata = { title: "Your account" };

export default async function AccountPage() {
  const token = await sessionToken();
  const [me, check] = await Promise.all([api.getMe(token), api.getDeletionCheck(token)]);
  const blockers = check.blockers;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-[28px] font-bold leading-[34px] text-nx-text">Your account</h1>
        <p className="mt-1 text-sm text-nx-text-muted">Signed in as {me.email}.</p>
      </div>

      <section aria-labelledby="delete-heading" className="space-y-4">
        <h2 id="delete-heading" className="text-xl font-semibold text-nx-text">Delete your account</h2>
        <Card className="max-w-2xl space-y-4 border-nx-danger">
          <div className="space-y-2 text-sm text-nx-text">
            <p className="font-medium">This cannot be undone.</p>
            <p>These are deleted at once:</p>
            <ul className="list-disc space-y-1 pl-5 text-nx-text-muted">
              <li>your account and your sign-in</li>
              <li>every organisation you own, with its targets, scans, reports, share links, API keys, plans and invitations</li>
              <li>your membership of other organisations</li>
            </ul>
            <p>These stay:</p>
            <ul className="list-disc space-y-1 pl-5 text-nx-text-muted">
              <li>what you created inside someone else&apos;s organisation, which stays with that organisation</li>
              <li>the security log, which keeps an anonymous record that you acted, shown as &ldquo;Former member&rdquo;</li>
              <li>invoices held by our payment provider, which we must keep for accounting</li>
            </ul>
          </div>

          {blockers.length > 0 ? (
            <div role="status" className="space-y-2 rounded-nx-md border border-nx-border bg-nx-surface p-3 text-sm">
              <p className="font-medium text-nx-text">Before you can delete your account:</p>
              <ul className="list-disc space-y-1 pl-5 text-nx-text">
                {blockers.map((b) => (
                  <li key={`${b.kind}-${b.org_id}`}>
                    {b.detail}{" "}
                    <Link
                      href={b.kind === "members" ? "/console/members" : "/dashboard/billing"}
                      className="text-nx-link underline underline-offset-2"
                    >
                      {b.kind === "members" ? "Open members" : "Open billing"}
                    </Link>
                  </li>
                ))}
              </ul>
              <p className="text-xs text-nx-text-muted">
                Switch to the organisation named above first if it is not the one you are viewing.
              </p>
            </div>
          ) : null}

          <DeleteAccountForm email={me.email} />
        </Card>
      </section>
    </div>
  );
}
