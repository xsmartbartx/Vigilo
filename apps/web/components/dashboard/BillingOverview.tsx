import type { BillingProductLine, BillingSummaryResponse } from "../../lib/types";
import { Badge, Card } from "../ui";
import { ManageSubscriptionButton } from "./ManageSubscriptionButton";

function money(cents: number, currency: string): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency.toUpperCase(),
    maximumFractionDigits: cents % 100 === 0 ? 0 : 2,
  }).format(cents / 100);
}

// Fixed to UTC so the date a customer sees does not shift with the viewer's zone.
function day(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

function priceCell(line: BillingProductLine): string {
  if (line.status === "free") return "Free";
  return `${money(line.amount_cents, line.currency)} / ${line.interval === "year" ? "year" : "month"}`;
}

function renewalCell(line: BillingProductLine) {
  if (line.status === "free" || !line.current_period_end) return <span className="text-nx-text-muted">—</span>;
  return line.cancel_at_period_end ? (
    <span className="text-nx-warning">Ends {day(line.current_period_end)}</span>
  ) : (
    <span>Renews {day(line.current_period_end)}</span>
  );
}

function action(line: BillingProductLine, orgId: string) {
  if (!line.can_purchase) return <span className="text-nx-text-muted">Not available to buy yet</span>;
  if (line.status === "active") return <ManageSubscriptionButton orgId={orgId} />;
  return (
    <a href="#plans" className="text-nx-link underline underline-offset-2">
      See plans
    </a>
  );
}

// One table for everything this organisation pays for, across products.
export function BillingOverview({ summary }: { summary: BillingSummaryResponse }) {
  const { monthly_cents: monthly, yearly_cents: yearly, currency } = summary.totals;
  const paying = summary.products.filter((p) => p.status === "active").length;

  return (
    <section aria-labelledby="overview" className="space-y-4">
      <h2 id="overview" className="text-xl font-semibold text-nx-text">
        What {summary.org_name} pays for
      </h2>

      <Card
        tabIndex={0}
        role="region"
        aria-label="Plans and prices by product"
        className="relative overflow-x-auto p-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-nx-accent"
      >
        <table className="w-full min-w-[640px] text-left text-sm">
          <caption className="sr-only">Plan, price and renewal for each product</caption>
          <thead className="border-b border-nx-border text-nx-text-muted">
            <tr>
              <th scope="col" className="px-4 py-3 font-medium">Product</th>
              <th scope="col" className="px-4 py-3 font-medium">Plan</th>
              <th scope="col" className="px-4 py-3 font-medium">Price</th>
              <th scope="col" className="px-4 py-3 font-medium">Next date</th>
              <th scope="col" className="px-4 py-3 font-medium">
                <span className="sr-only">Action</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {summary.products.map((line) => (
              <tr key={line.product_slug} className="border-b border-nx-border align-top last:border-0">
                <th scope="row" className="px-4 py-3 font-medium text-nx-text">
                  {line.product_name}
                </th>
                <td className="px-4 py-3 capitalize text-nx-text">
                  {line.plan_id}{" "}
                  {line.cancel_at_period_end ? <Badge tone="warning">Cancelling</Badge> : null}
                </td>
                <td className="px-4 py-3 text-nx-text">{priceCell(line)}</td>
                <td className="px-4 py-3 text-nx-text">{renewalCell(line)}</td>
                <td className="px-4 py-3">{action(line, summary.org_id)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <div className="space-y-1 text-sm">
        {paying === 0 ? (
          <p className="text-nx-text-muted">Nothing is billed: every product is on its free plan.</p>
        ) : (
          <>
            {monthly > 0 ? (
              <p className="text-nx-text">
                <span className="font-medium">{money(monthly, currency)}</span> billed monthly
              </p>
            ) : null}
            {yearly > 0 ? (
              <p className="text-nx-text">
                <span className="font-medium">{money(yearly, currency)}</span> billed yearly
              </p>
            ) : null}
            <p className="text-xs text-nx-text-muted">
              Prices shown are the plan prices; your invoices come from Stripe and are the record of what you
              were charged. Taxes are not included.
            </p>
          </>
        )}
      </div>
    </section>
  );
}
