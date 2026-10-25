# Legal and tax review checklist

The terms, privacy, acceptable-use and cookie pages describe what Vigilo actually does, but no
lawyer has reviewed them, so each page carries a DRAFT banner (`apps/web/components/DraftBanner.tsx`).
Remove the banner only after a review. This list is what to hand a lawyer or accountant. It was
written from the code and the production setup on 2026-10-25; it is not legal advice.

## Facts a lawyer will ask for (to fill in)
- [ ] The legal entity that sells Vigilo: name, registered address, registration and VAT numbers.
      The pages currently say only "Vigilo" (`brand.config.json` -> `legalName`).
- [ ] Governing law and the court or arbitration venue. Not stated in the terms today.
- [ ] Refund and cancellation policy. The terms say a cancellation takes effect at the end of the paid
      period and say nothing about refunds or consumer withdrawal rights (EU: 14 days for digital
      services, with the usual waiver once the service starts).
- [ ] Who the contact points are. `support@`, `abuse@` and `security@onenexora.com` are named in the
      pages; the mailboxes must exist before launch.

## Tax
- [ ] **Vigilo is sold through Stripe directly, so NEXORA is the seller, not Stripe.** Stripe is a payment
      processor, not a merchant of record: VAT or sales tax on subscriptions is NEXORA's responsibility.
      (The pages used to say "merchant-of-record"; that was corrected.)
- [ ] Decide how tax is collected: Stripe Tax (needs registrations in each jurisdiction where a threshold
      is crossed, and a tax setup in the Stripe dashboard) or manual VAT handling. EU consumer sales of
      digital services are taxed where the customer lives (OSS scheme).
- [ ] Prices are shown as $29 / month and $290 / year with no statement of whether tax is included.

## Personal data and processors (privacy policy accuracy)
Data flows as of today. Each processor needs a data-processing agreement and, for transfers outside
the EEA, a transfer mechanism (SCCs or an adequacy decision):
| Processor | What it receives | Where |
|---|---|---|
| Oracle Cloud (OCI) | all application data, database, backups | Frankfurt (EU) |
| Clerk | email, sign-in identity, organisation membership | United States |
| Stripe | email, plan, payment details (card data never reaches Vigilo) | United States / EU |
| Anthropic | redacted finding summaries to write remediation text | United States |
| Postmark | invitation and notification emails (not yet enabled) | United States |
| Sentry (optional) | error reports, only if `SENTRY_DSN` is set | per configuration |
- [ ] Privacy policy lists every processor above (Stripe, Anthropic and Postmark are only named
      generically today).
- [ ] Retention: scan evidence is deleted after 90 days; reports and scores are kept while the account
      exists; backups are kept 14 days on the server.
- [ ] A data-processing agreement for customers who scan on behalf of their company.
- [ ] Legal basis for each processing purpose (contract, legitimate interest, consent) and the cookie
      banner decision: the cookie page lists what is set; confirm whether a consent banner is needed.

## Scanning authority (acceptable-use policy)
- [ ] Active-tier scans run only after the site owner proves control (DNS record, well-known file or meta
      tag). Have the lawyer confirm the policy and the owner-verification wording are enough for the
      jurisdictions you sell in.
- [ ] A takedown and complaint process: `abuse@onenexora.com` must be monitored.

## Before removing the DRAFT banner
1. Everything above is filled in or consciously declined.
2. A lawyer has reviewed the four pages.
3. The "Last updated" dates are set to the review date.
