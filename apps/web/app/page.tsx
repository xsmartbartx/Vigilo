import Link from "next/link";
import { ScanSubmitForm } from "../components/ScanSubmitForm";
import { LandingSections } from "../components/marketing/LandingSections";
import { SiteShell } from "../components/vigilo-site/SiteChrome";
import { brand } from "../lib/brand";
import { NEXORA_URL } from "../lib/site";

export const metadata = {
  title: `${brand.name}: ${brand.shortDescription}`,
  description: brand.shortDescription,
};

// What the product does, stated as facts about how it works (no counts of users or
// customers: there is nothing to count yet).
const FACTS = [
  { value: "64", label: "checks, from security headers to exposed keys and databases" },
  { value: "1", label: "recorded request behind every finding, shown with the answer it got" },
  { value: "0", label: "code access needed: it looks at your site the way a stranger would" },
] as const;

export default function HomePage() {
  return (
    <SiteShell>
      <section aria-labelledby="hero" className="mx-auto w-full max-w-[1120px] px-4 pb-16 pt-16 text-center sm:px-6 sm:pt-24">
        <p className="text-sm font-medium text-nx-accent">
          {brand.name} <span className="text-nx-text-muted">· a NEXORA product</span>
        </p>
        <h1
          id="hero"
          className="mx-auto mt-4 max-w-4xl text-[36px] font-bold leading-[40px] tracking-tight text-nx-text sm:text-[56px] sm:leading-[60px]"
        >
          Other scanners bury you in alerts. {brand.name} shows only what it can prove.
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-nx-text-muted sm:text-xl">
          Paste your live URL. Get a plain-language report where every problem carries its evidence and a fix you
          can paste into your AI coding tool.
        </p>
        <div id="scan" className="mx-auto mt-10 flex max-w-xl scroll-mt-24 justify-center">
          <ScanSubmitForm />
        </div>
        <p className="mt-4 text-sm text-nx-text-muted">
          The first scan is free and needs only your email.{" "}
          <Link href="/#how" className="text-nx-accent underline underline-offset-2">
            See how it works
          </Link>
        </p>
      </section>

      <section aria-label={`${brand.name} in numbers`} className="border-y border-nx-border bg-nx-surface">
        <dl className="mx-auto grid w-full max-w-[1120px] gap-8 px-4 py-12 text-center sm:grid-cols-3 sm:px-6">
          {FACTS.map((fact) => (
            <div key={fact.label}>
              <dt className="text-[44px] font-bold leading-[48px] text-nx-text">{fact.value}</dt>
              <dd className="mx-auto mt-2 max-w-[240px] text-sm text-nx-text-muted">{fact.label}</dd>
            </div>
          ))}
        </dl>
      </section>

      <LandingSections />

      <section aria-labelledby="platform" className="border-t border-nx-border bg-nx-surface">
        <div className="mx-auto flex w-full max-w-[1120px] flex-wrap items-center justify-between gap-4 px-4 py-10 sm:px-6">
          <div className="max-w-xl">
            <h2 id="platform" className="text-lg font-semibold text-nx-text">
              {brand.name} is one product on NEXORA
            </h2>
            <p className="mt-1 text-sm text-nx-text-muted">
              The same account and organisation work across NEXORA products. See what else is on the platform.
            </p>
          </div>
          <a
            href={`${NEXORA_URL}/products`}
            className="inline-flex h-10 items-center rounded-nx-md border border-nx-border-input px-4 text-sm font-semibold text-nx-text hover:bg-nx-bg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-nx-accent"
          >
            Explore NEXORA products
          </a>
        </div>
      </section>
    </SiteShell>
  );
}
