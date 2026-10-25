import Link from "next/link";
import { PlanTable } from "../../components/marketing/PlanTable";
import { SiteShell } from "../../components/vigilo-site/SiteChrome";
import { PLANS } from "../../lib/nexora/catalog";
import { brand } from "../../lib/brand";

export const metadata = { title: `Pricing | ${brand.name}` };

export default function PricingPage() {
  return (
    <SiteShell>
      <div className="mx-auto w-full max-w-[1120px] space-y-8 px-4 py-12 sm:px-6">
        <div className="max-w-2xl space-y-2">
          <h1 className="text-[40px] font-bold leading-[44px] text-nx-text">{brand.name} pricing</h1>
          <p className="text-nx-text-muted">
            Start free. Upgrade when you want active checks, daily monitoring and the API. Cancel any time from the
            billing page; your plan runs to the end of the period you paid for.
          </p>
        </div>
        <PlanTable
          slug="vigilo"
          tiers={PLANS.vigilo}
          actions={{
            free: { href: "/#scan", label: "Scan free" },
            // Signed-out visitors are sent to sign in and come back to the billing page, where
            // the Upgrade buttons start Stripe Checkout.
            pro: { href: "/dashboard/billing", label: "Get Pro" },
          }}
        />
        <p className="text-sm text-nx-text-muted">
          Questions about a plan?{" "}
          <Link href="/#faq" className="text-nx-accent underline underline-offset-2">
            Read the FAQ
          </Link>{" "}
          or <a href={`mailto:${brand.supportEmail}`} className="text-nx-accent underline underline-offset-2">write to us</a>.
        </p>
      </div>
    </SiteShell>
  );
}
