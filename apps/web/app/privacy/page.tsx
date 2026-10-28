import Link from "next/link";
import { DraftBanner } from "../../components/DraftBanner";
import { Footer } from "../../components/Footer";
import { brand } from "../../lib/brand";

export const metadata = { title: `Privacy Policy — ${brand.name}` };

export default function PrivacyPolicyPage() {
  return (
    <>
      <DraftBanner />
      <main className="flex-1 mx-auto w-full max-w-2xl px-6 py-12 space-y-6">
        <div>
          <Link href="/" className="text-sm hover:underline">
            &larr; Back to {brand.name}
          </Link>
          <h1 className="mt-4 text-2xl font-bold">Privacy Policy</h1>
          <p className="mt-1 text-sm text-black/60 dark:text-white/60">
            Last updated: October 2026
          </p>
        </div>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">What {brand.name} does</h2>
          <p>
            {brand.name} ({brand.legalName}) is a security and compliance
            scanner. You submit a URL; we run a series of passive and, where
            authorized, active checks against it and produce a report. This
            policy covers the personal data we collect from you as a user of
            the service, and separately, how we handle data belonging to the
            sites we scan.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">Data we collect from you</h2>
          <ul className="list-disc pl-6 space-y-1">
            <li>
              <strong>Email address</strong> — required to submit a scan or
              create an account, used to identify your account and to send you
              the transactional emails described below: a summary when a scan
              you requested finishes, alerts from monitoring you have set up,
              and organisation invitations. The full report is shown on screen.
              We do not send marketing email.
            </li>
            <li>
              <strong>Account and authentication data</strong> — if you sign
              in, our authentication provider (Clerk) manages your
              credentials; we store the resulting account identifier, not
              your password.
            </li>
            <li>
              <strong>Submitted target URLs</strong> — the sites you ask us
              to scan, and the reports we generate from those scans.
            </li>
            <li>
              <strong>Billing information</strong> — if you subscribe to a
              paid plan, payment details are collected and processed
              directly by our payment provider, Stripe. We never receive
              your card details. We store your plan and subscription status,
              the Stripe customer and subscription identifiers, the billing
              interval (monthly or yearly), the end of the current billing
              period, and whether you have asked to cancel.
            </li>
            <li>
              <strong>Operational logs</strong> — standard request logs and
              an audit trail of authorization decisions (what was scanned,
              at what tier, and why), kept for security and debugging.
            </li>
          </ul>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">
            How we handle data about scanned sites
          </h2>
          <p>
            A scan captures evidence — response headers, page content
            excerpts, and similar technical artifacts — needed to justify
            each finding in your report. Before this evidence is stored, any
            value that looks like a secret (an API key, token, or
            credential) is redacted; only a fingerprint of it is kept, never
            the raw value. Evidence bundles are stored for a limited period
            (90 days) and then deleted; the resulting report and score are
            retained for as long as your account exists.
          </p>
          <p>
            Passive-tier scanning only ever makes requests a normal visitor
            or search-engine crawler would make. Active-tier scanning — path
            enumeration and deeper probing — only runs once we have verified
            you own or control the target, via a DNS record, a well-known
            file, or a meta tag you control.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">People invited to an organisation</h2>
          <p>
            When an organisation owner or admin invites someone, we store the
            invited email address, the role offered and the inviter until the
            invitation is accepted, withdrawn or replaced. We email the invited
            address a one-time link (the inviter also sees the link), through
            our email provider. If you were not expecting one, ignore it:
            nothing happens unless you accept.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">Who we share data with</h2>
          <p>
            We use a small number of subprocessors to run the service:
            our cloud hosting and database provider, our authentication
            provider (Clerk), our payment provider (Stripe), our email provider
            (Postmark), which delivers the transactional emails described above
            and so receives the recipient address and the message content, and
            an LLM provider used to generate plain-language remediation
            guidance for findings. Data sent to the LLM provider is limited
            to already-redacted finding summaries — never raw evidence or
            account credentials. We do not sell your data.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">Your rights</h2>
          <p>
            You can delete your account yourself under Account in the
            console. That removes your account, the organisations you own
            and everything in them, and your sign-in. Things you created in
            someone else&apos;s organisation stay with that organisation, our
            security log keeps an anonymous record that you acted, and our
            payment provider keeps invoices it is required to keep. You can
            also request a copy of the data we hold about you, or ask us to
            correct it, by emailing{" "}
            <a href={`mailto:${brand.supportEmail}`} className="underline">
              {brand.supportEmail}
            </a>
            . If you are a site owner and want a scan of your site removed
            or want your site excluded from future scanning regardless of
            who submits it, see our{" "}
            <Link href="/aup" className="underline">
              Acceptable Use Policy
            </Link>
            .
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">Contact</h2>
          <p>
            Questions about this policy can be sent to{" "}
            <a href={`mailto:${brand.supportEmail}`} className="underline">
              {brand.supportEmail}
            </a>
            .
          </p>
        </section>
      </main>
      <Footer />
    </>
  );
}
