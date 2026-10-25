# Connecting another product engine: a plan, not a build

Status: **draft for decision.** Nothing here is built. It is grounded in what this repository
contains today and in what the deploy history shows about the host. Where I do not know
something, it is listed under "Decisions needed", not guessed.

## What exists today

- **This repository is Vigilo only.** The platform shell (home, products, pricing, console,
  organisations, members, audit, usage) lives here, but only Vigilo's engine does.
- **The other four products are not in this repo.** The shared host deploys them separately:
  Sentinel, CSPM and Gateway from `/opt/nexora` (`deploy.sh nexora ... sentinel cspm gateway`),
  and NeuraWall from `/opt/neurawall`. The catalog (`apps/web/lib/nexora/catalog.ts`) shows them as
  "Coming soon" and `AVAILABLE_PRODUCTS = ("vigilo",)` stops the API enabling them.
- **Shell pieces that are already product-aware**, so a second engine does not need them rebuilt:
  - `product_enablements` (which organisation has which product on) and the launcher UI.
  - Usage counters keyed by organisation, product and meter.
  - API key scopes shaped `product:resource:action`; other products' scopes are rejected until
    they are connected.
  - The audit log and roles are organisation-wide, not Vigilo-specific.
- **What is Vigilo-specific and would need generalising:** billing. `price_to_plan()`, the webhook
  mapping and the Stripe objects (one Pro product, two prices) assume one product. The plan
  ladders for the other products exist only as static marketing data.

## The one decision that shapes everything: who bills

Upstream's `origin/main` briefly carried a different design: organisation plans come from a
separate **NEXORA Core** service, and Vigilo's checkout returns 409 with a link to it. This branch
chose the opposite (billing inside Vigilo, per organisation). With four more products, that choice
decides the work:

| | Shell bills (current) | Core bills (upstream's idea) |
|---|---|---|
| Where subscriptions live | This repo's Stripe integration, one price set per product | A separate service; engines receive a signed "plan changed" call |
| Work to add a product | Add its Stripe prices, webhook mapping and plan ladder here | Add a consumer of Core's signed plan updates per engine |
| Fits if | Products are sold one at a time from this site | One checkout and one invoice cover all products |

I would not start an engine until this is settled, because it decides what "connected" means.

## Per-engine size (my estimates, from how each product is described)

| Engine | Shape | Size | Main difficulty |
|---|---|---|---|
| Sentinel (log analysis) | Paste a sample, get a short list of findings: the closest to Vigilo's scan flow | M | Defining the finding format and redaction of pasted logs |
| CSPM (cloud config audit) | Paste a configuration, get misconfigurations | M | Same shape as Sentinel; parsers per cloud |
| Gateway (LLM governance) | A live proxy every model call goes through | L | Metering and latency in the request path; it is infrastructure, not a report |
| NeuraWall (AI firewall) | Self-hosted nodes, billed per node, license-gated retention | L | Node enrolment and license keys; a different model from "scans" |

## Suggested first step

Connect **one thin engine (Sentinel or CSPM)** through a small contract, and let that settle the
shape for the rest:

1. **Engine contract.** Each engine exposes, behind the shell's login: create an analysis, read its
   result, and report usage. The shell sends the signed-in user's token and the active organisation.
2. **Shell side.** Add the product to `AVAILABLE_PRODUCTS`, show it as live, route its pages, count
   its usage in the existing meters, and check the product-scoped API key scope.
3. **Billing.** Follow whichever model is chosen above; for "shell bills", extend the Stripe setup
   script to create that product's prices and generalise the price-to-plan mapping.
4. **Verify.** A browser spec as for Vigilo (sign in, run, see the result, hit the limit), and the
   same smoke and uptime checks for the engine's URL.

## Decisions needed from you

1. Who bills: the shell, or NEXORA Core?
2. Which engine first, and is its code in a repository I can read (and where)?
3. Should engines share this Clerk instance and login, or have their own?
4. Do you want the engines reachable only through the shell, or also at their own domains?
5. Is the Sentinel/CSPM/Gateway/NeuraWall pricing in the catalog final? It is public marketing
   data today and would become real Stripe prices.

No building starts until questions 1 and 2 are answered.
