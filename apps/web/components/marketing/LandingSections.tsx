import Link from "next/link";
import { PLANS } from "../../lib/nexora/catalog";
import { Card } from "../ui";

const STEPS = [
  { title: "Paste your URL", body: "No install and no code access. Vigilo looks at your app the way a stranger would." },
  { title: "We check what we can prove", body: "Each finding carries the request we sent and the answer we got back. Anything we couldn't check is listed separately." },
  { title: "Paste the fix", body: "Every problem comes with a prompt written for your AI coding tool. Paste it, redeploy, scan again." },
];

const FEATURES = [
  { title: "Proof, not guesses", body: "A finding only appears when a recorded request shows it. No \"possible\" issues padding the list." },
  { title: "Honest about gaps", body: "Checks we couldn't run are shown as their own list instead of counting as passed." },
  { title: "Fixes you can paste", body: "A prompt for your AI coding tool, written for the exact problem found, not a link to a standards document." },
  { title: "Accept a risk once", body: "Mark a known finding as accepted with a reason. It stays visible but stops nagging." },
  { title: "Catches the regression", body: "Scheduled re-scans warn you when the fifth deploy brings an old problem back." },
  { title: "Fits your pipeline", body: "CLI, GitHub Action with SARIF upload, a REST API and an MCP server for your editor." },
];

const FAQ = [
  { q: "Do I need to give you my code?", a: "No. The free scan only looks at your deployed site. Scanning more deeply needs you to prove you own the site first." },
  { q: "Will a scan break my app?", a: "Scans are non-destructive and rate-limited. Checks that go further than reading public pages only run on sites you have verified." },
  { q: "What do you scan for?", a: "64 checks across security headers, TLS, sessions, exposed keys and databases, deployment hygiene, and legal pages such as privacy and cookie consent." },
  { q: "Is the fix prompt always right?", a: "It is generated from the finding and your detected stack, and a re-scan tells you whether it worked. Review changes before you ship them." },
  { q: "Can I cancel any time?", a: "Yes, from the billing page, with no email or call needed. Your plan runs to the end of the period you paid for." },
];

export function LandingSections() {
  const vigilo = PLANS.vigilo;
  return (
    <div className="mx-auto w-full max-w-[1120px] space-y-16 px-4 py-16 sm:px-6">
      <section aria-labelledby="problem" className="max-w-2xl space-y-3">
        <h2 id="problem" className="text-[28px] font-bold leading-[34px] text-nx-text">
          Most scanners hand you a pile
        </h2>
        <p className="text-nx-text-muted">
          A long list with no proof is easy to ignore, and easy to get wrong in both directions.
          And if your app came out of an AI tool, the same few mistakes keep coming back: a
          database anyone can read, a key compiled into the page, no headers, no privacy policy.
          You need to know which ones are real and what to do about them.
        </p>
      </section>

      <section aria-labelledby="how" className="space-y-4">
        <h2 id="how" className="scroll-mt-24 text-[28px] font-bold leading-[34px] text-nx-text">How it works</h2>
        <ol className="grid gap-4 md:grid-cols-3">
          {STEPS.map((s, i) => (
            <li key={s.title}>
              <Card className="h-full space-y-2">
                <p className="text-sm font-semibold text-nx-accent">Step {i + 1}</p>
                <h3 className="text-lg font-semibold text-nx-text">{s.title}</h3>
                <p className="text-sm text-nx-text-muted">{s.body}</p>
              </Card>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="features" className="space-y-4">
        <h2 id="features" className="scroll-mt-24 text-[28px] font-bold leading-[34px] text-nx-text">What you get</h2>
        <ul className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <li key={f.title}>
              <Card className="h-full space-y-2">
                <h3 className="text-lg font-semibold text-nx-text">{f.title}</h3>
                <p className="text-sm text-nx-text-muted">{f.body}</p>
              </Card>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="pricing" className="space-y-4">
        <h2 id="pricing" className="scroll-mt-24 text-[28px] font-bold leading-[34px] text-nx-text">Pricing</h2>
        <ul className="grid max-w-3xl gap-4 md:grid-cols-2">
          {vigilo.map((tier) => (
            <li key={tier.id}>
              <Card className="h-full space-y-2">
                <h3 className="text-lg font-semibold text-nx-text">{tier.name}</h3>
                <p className="text-[28px] font-bold text-nx-text">
                  {tier.monthlyUsd === 0 ? "$0" : `$${tier.monthlyUsd}`}
                  {tier.monthlyUsd > 0 && <span className="text-sm font-normal text-nx-text-muted"> / month</span>}
                </p>
                <p className="text-sm text-nx-text">{tier.limit}</p>
                {tier.perks && <p className="text-sm text-nx-text-muted">{tier.perks}</p>}
              </Card>
            </li>
          ))}
        </ul>
        <p className="text-sm text-nx-text-muted">
          Pay yearly for $290 instead of $348. <Link href="/pricing" className="text-nx-accent underline underline-offset-2">Compare plans</Link>
        </p>
      </section>

      <section aria-labelledby="faq" className="max-w-2xl space-y-4">
        <h2 id="faq" className="scroll-mt-24 text-[28px] font-bold leading-[34px] text-nx-text">Questions</h2>
        <dl className="space-y-4">
          {FAQ.map((item) => (
            <div key={item.q}>
              <dt className="font-semibold text-nx-text">{item.q}</dt>
              <dd className="mt-1 text-sm text-nx-text-muted">{item.a}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section aria-labelledby="cta" className="rounded-nx-lg border border-nx-border bg-nx-surface p-8 text-center">
        <h2 id="cta" className="text-[28px] font-bold leading-[34px] text-nx-text">Scan the site you just shipped</h2>
        <p className="mt-2 text-nx-text-muted">The first scan is free and needs only your email.</p>
        <a
          href="#target_url"
          className="mt-4 inline-flex h-10 items-center rounded-nx-md bg-nx-accent px-4 text-sm font-semibold text-nx-on-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-nx-accent"
        >
          Scan it
        </a>
      </section>
    </div>
  );
}
