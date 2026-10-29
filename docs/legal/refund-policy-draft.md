# Refund and cancellation policy: DRAFT

> **Draft for lawyer review. Not legal advice and not published.** It describes how billing
> actually works today (see "Facts this draft relies on") and proposes wording for the choices
> that are still open (marked **[DECIDE]**). Nothing here is on the website. Items in
> `[BRACKETS]` must be filled in by you. After review, the final text goes into the terms page
> (`apps/web/app/terms/page.tsx`, "Plans and billing") and the pricing FAQ.

## Facts this draft relies on (verified in the code and the Stripe setup, 2026-10-29)
- **Plans:** Free ($0: 1 target, 3 scans a month) and Pro ($29 a month or $290 a year: 25 targets,
  unlimited scans, active checks, daily monitoring, API, white-label reports).
- **Payment:** card payments through Stripe Checkout. NEXORA is the seller; Stripe is only the
  payment processor.
- **Renewal:** subscriptions renew automatically until cancelled.
- **Cancellation:** the customer cancels in the billing portal ("Manage or cancel"). The plan
  stays Pro until the end of the period already paid for, then returns to Free. Nothing is
  charged again after cancelling.
- **Refunds are not automatic.** Nothing in the product refunds money; a refund is made by hand
  in the Stripe dashboard.
- **Team organisations** billed through NEXORA Core follow the same Stripe rules; the
  organisation's owner or admin is the customer.

## 1. Proposed policy text (customer-facing)

### Cancelling
You can cancel your subscription at any time from **Billing → Manage or cancel**. Cancelling stops
future renewals. You keep Pro until the end of the billing period you have already paid for, and
your account then moves to the Free plan. We do not charge you again after you cancel.

### Refunds
**[DECIDE: choose A or B.]**

**Option A, a short money-back window (recommended for a new product):**
If you are not satisfied, ask us within **[14] days of your first payment** for a plan and we will
refund that payment in full, no questions asked. This applies once per customer. After that
window, payments are not refundable, except as set out below or where the law requires otherwise.

**Option B, no discretionary refunds:**
Payments are not refundable once made, except as set out below or where the law requires
otherwise. You can cancel at any time to stop future charges.

### Refunds we will always make
- **A charge you did not authorise, or a duplicate charge:** refunded in full.
- **A renewal charged after you cancelled in time:** refunded in full.
- **A service failure on our side** that stopped you using a paid feature for a significant
  period **[DECIDE: define "significant", for example more than 24 hours in a billing period]**:
  a refund or credit for the affected period, at our choice.
- **Annual plans:** **[DECIDE: for Option A only the first-14-day window applies; or add a
  pro-rata refund for the unused months if you cancel an annual plan early]**.

### Consumers in the EU and UK
If you are a consumer, you may have a statutory right to withdraw from a distance contract within
14 days. For digital services you agree that we start providing the service immediately and, if
you withdraw after it has started, you pay a proportionate amount for what you have used, as the
law allows. **[LAWYER: confirm the exact wording and the consent checkbox needed at checkout for
the immediate-performance waiver; Stripe Checkout can show a custom terms notice.]**

### How to ask
Email **support@onenexora.com** from the address on your account, with your account email and the
date of the payment. We reply within **[2] business days**.

### How refunds are paid
Refunds go back to the original payment method through Stripe. Banks usually show them within
**5 to 10 business days**. Taxes charged on a payment are refunded with it. Stripe's processing
fee is not returned to us, and we do not charge it to you.

### Failed payments
If a renewal payment fails, Stripe retries it for a period. If it still fails the subscription is
cancelled and the account returns to the Free plan. No refund is due for a failed payment.

### Chargebacks
Please contact us before disputing a charge with your bank; we resolve genuine problems quickly.
If a chargeback is opened we may suspend the account while it is reviewed.

### Misuse
We may refuse a refund, and close the account, where the service was used in breach of the
Acceptable Use Policy (for example scanning sites you do not control).

### Changes to prices
We will tell you by email at least **[30] days** before a price increase applies to your next
renewal, and you can cancel before it applies. *(Requires email to be switched on; see the
email setup notes.)*

## 2. Decisions needed from you (the **[DECIDE]** items)
1. **A or B?** A money-back window costs a little in fees and refunds but removes most friction
   and most chargebacks for a new, unknown product. B is simpler but invites disputes.
2. **Length of the window** (7, 14 or 30 days).
3. **Annual plans:** first-window only, or pro-rata for unused months.
4. **What counts as a service failure** that earns a credit or refund.
5. **Response time** you can actually keep for support@ (the draft promises 2 business days).

## 3. Product and operations changes this policy implies
- [ ] **Terms page:** replace the "Plans and billing" paragraph with the final wording above, and
      link the policy from the pricing page and the checkout page.
- [ ] **Stripe:** in the dashboard, add the policy link under Settings → Public details, and
      consider a "terms of service" consent box on Checkout.
- [ ] **A refund runbook for you:** Stripe dashboard → Payments → the payment → Refund. Cancel
      the subscription immediately in the same session if the customer asked to stop (Subscriptions
      → Cancel → Immediately), so the plan returns to Free and nothing renews.
- [ ] **Email:** several promises here (price-change notice, receipts, reply times) rely on
      email working; Postmark is not switched on yet.
- [ ] **Record keeping:** keep refund records for the period your tax authority requires.
