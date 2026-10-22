#!/usr/bin/env python3
"""Create Vigilo's Stripe objects: the Pro product, its monthly and yearly
prices, the customer-portal configuration and (optionally) the webhook endpoint.

Safe to re-run: every object is looked up first (prices by `lookup_key`, the
product and portal configuration by `metadata.vigilo`, the webhook by URL) and
only created when missing. The default is a dry run that only reads.

    export STRIPE_SECRET_KEY=sk_test_...        # from your shell, never from chat
    uv run python scripts/stripe_setup.py --mode test                # dry run
    uv run python scripts/stripe_setup.py --mode test --apply
    uv run python scripts/stripe_setup.py --mode live --apply --webhook-url https://example.com/v1/billing/webhook

`--mode` must match the key (`sk_test_`/`rk_test_` for test, `sk_live_`/`rk_live_`
for live); a mismatch stops the script before any request is sent. The key is
read from the environment only and is never printed.

Prints the lines to paste into the environment file. The webhook signing secret
is shown by Stripe only when the endpoint is created, so it is printed once.
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx

API = "https://api.stripe.com/v1"
PRODUCT_NAME = "Vigilo Pro"
LOOKUP_KEYS = {"monthly": "vigilo_pro_monthly", "yearly": "vigilo_pro_yearly"}
# What the app's webhook handler interprets (vigilo_billing.webhooks).
WEBHOOK_EVENTS = [
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_failed",
]


class SetupError(Exception):
    pass


def key_mode(key: str) -> str | None:
    if key.startswith(("sk_test_", "rk_test_")):
        return "test"
    if key.startswith(("sk_live_", "rk_live_")):
        return "live"
    return None


def prices_from_plan() -> tuple[int, int, str]:
    """The amounts the app displays, so Stripe and the pricing page cannot drift."""
    try:
        from vigilo_billing import PLANS
    except ModuleNotFoundError as exc:
        raise SetupError(
            "run this through the project environment: uv run python scripts/stripe_setup.py ..."
        ) from exc

    pro = PLANS["pro"]
    return pro.price_cents, pro.price_cents_yearly, pro.currency


class Stripe:
    def __init__(self, key: str, transport: httpx.BaseTransport | None = None):
        self._client = httpx.Client(base_url=API, auth=(key, ""), timeout=20.0, transport=transport)

    def get(self, path: str, **params) -> dict:
        return self._check(self._client.get(path, params=params))

    def post(self, path: str, data: dict) -> dict:
        return self._check(self._client.post(path, data=data))

    @staticmethod
    def _check(response: httpx.Response) -> dict:
        if response.status_code >= 400:
            try:
                message = response.json()["error"]["message"]
            except Exception:  # noqa: BLE001
                message = f"HTTP {response.status_code}"
            raise SetupError(f"Stripe rejected the request ({response.status_code}): {message}")
        return response.json()


def find_product(stripe: Stripe) -> dict | None:
    products = stripe.get("/products", active="true", limit=100)["data"]
    for product in products:
        if product.get("metadata", {}).get("vigilo") == "pro":
            return product
    # A product with our name but not our marker (made by hand or by an earlier tool) would
    # silently be duplicated, and the app may already sell its prices. Stop and say so.
    unmarked = [p for p in products if p.get("name") == PRODUCT_NAME]
    if unmarked:
        raise SetupError(
            f"an active product named '{PRODUCT_NAME}' ({unmarked[0]['id']}) exists without the "
            "metadata vigilo=pro. Add that metadata to it in the Stripe dashboard to adopt it "
            "(or archive it first), then re-run. Nothing was created."
        )
    return None


def find_price(stripe: Stripe, lookup_key: str) -> dict | None:
    data = stripe.get("/prices", **{"lookup_keys[]": lookup_key, "active": "true"})["data"]
    return data[0] if data else None


def find_portal(stripe: Stripe) -> dict | None:
    for config in stripe.get("/billing_portal/configurations", limit=100)["data"]:
        if config.get("metadata", {}).get("vigilo") == "portal":
            return config
    return None


def find_webhook(stripe: Stripe, url: str) -> dict | None:
    for endpoint in stripe.get("/webhook_endpoints", limit=100)["data"]:
        if endpoint["url"] == url:
            return endpoint
    return None


def run(stripe: Stripe, *, apply: bool, webhook_url: str | None, out=print) -> dict[str, str]:
    monthly_cents, yearly_cents, currency = prices_from_plan()
    env: dict[str, str] = {}

    def say(action: str, what: str) -> None:
        out(f"  {action:<10} {what}")

    product = find_product(stripe)
    if product:
        say("exists", f"product {product['id']}")
    elif apply:
        product = stripe.post("/products", {"name": PRODUCT_NAME, "metadata[vigilo]": "pro"})
        say("created", f"product {product['id']}")
    else:
        say("would add", f"product '{PRODUCT_NAME}'")

    for label, cents, interval in (
        ("monthly", monthly_cents, "month"),
        ("yearly", yearly_cents, "year"),
    ):
        lookup = LOOKUP_KEYS[label]
        price = find_price(stripe, lookup)
        if price:
            if price["unit_amount"] != cents or price["currency"] != currency:
                raise SetupError(
                    f"price {price['id']} ({lookup}) is {price['unit_amount']} {price['currency']} "
                    f"but the app charges {cents} {currency}. Prices are immutable in Stripe: "
                    "archive it in the dashboard, then re-run."
                )
            say("exists", f"{label} price {price['id']}")
        elif apply and product:
            price = stripe.post(
                "/prices",
                {
                    "product": product["id"],
                    "unit_amount": str(cents),
                    "currency": currency,
                    "recurring[interval]": interval,
                    "lookup_key": lookup,
                },
            )
            say("created", f"{label} price {price['id']} ({cents / 100:.2f} {currency}/{interval})")
        else:
            say("would add", f"{label} price {cents / 100:.2f} {currency}/{interval}")
        if price:
            env["STRIPE_PRICE_ID_PRO" if label == "monthly" else "STRIPE_PRICE_ID_PRO_YEARLY"] = (
                price["id"]
            )

    portal = find_portal(stripe)
    if portal:
        say("exists", f"portal configuration {portal['id']}")
    elif apply and product and "STRIPE_PRICE_ID_PRO" in env and "STRIPE_PRICE_ID_PRO_YEARLY" in env:
        portal = stripe.post(
            "/billing_portal/configurations",
            {
                "metadata[vigilo]": "portal",
                "business_profile[headline]": "Manage your Vigilo subscription",
                "features[invoice_history][enabled]": "true",
                "features[payment_method_update][enabled]": "true",
                "features[customer_update][enabled]": "true",
                "features[customer_update][allowed_updates][0]": "email",
                "features[customer_update][allowed_updates][1]": "address",
                # One-click cancel, effective at the end of the paid period.
                "features[subscription_cancel][enabled]": "true",
                "features[subscription_cancel][mode]": "at_period_end",
                # Switch between the monthly and yearly price.
                "features[subscription_update][enabled]": "true",
                "features[subscription_update][default_allowed_updates][0]": "price",
                "features[subscription_update][proration_behavior]": "create_prorations",
                "features[subscription_update][products][0][product]": product["id"],
                "features[subscription_update][products][0][prices][0]": env["STRIPE_PRICE_ID_PRO"],
                "features[subscription_update][products][0][prices][1]": env[
                    "STRIPE_PRICE_ID_PRO_YEARLY"
                ],
            },
        )
        say("created", f"portal configuration {portal['id']}")
    else:
        say("would add", "portal configuration (cancel at period end, plan switch, invoices)")
    if portal:
        env["STRIPE_PORTAL_CONFIGURATION_ID"] = portal["id"]

    if webhook_url:
        endpoint = find_webhook(stripe, webhook_url)
        if endpoint:
            say("exists", f"webhook {endpoint['id']} (its signing secret is not retrievable)")
        elif apply:
            data = {"url": webhook_url, "description": "Vigilo billing"}
            for i, event in enumerate(WEBHOOK_EVENTS):
                data[f"enabled_events[{i}]"] = event
            endpoint = stripe.post("/webhook_endpoints", data)
            say("created", f"webhook {endpoint['id']}")
            env["STRIPE_WEBHOOK_SECRET"] = endpoint["secret"]
        else:
            say("would add", f"webhook endpoint {webhook_url}")
    return env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--mode", choices=["test", "live"], required=True)
    parser.add_argument(
        "--apply", action="store_true", help="create what is missing (default: dry run)"
    )
    parser.add_argument("--webhook-url", help="also create this webhook endpoint")
    args = parser.parse_args(argv)

    key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    if not key:
        print("STRIPE_SECRET_KEY is not set in the environment.", file=sys.stderr)
        return 2
    actual = key_mode(key)
    if actual is None:
        print("STRIPE_SECRET_KEY is not a Stripe secret or restricted key.", file=sys.stderr)
        return 2
    if actual != args.mode:
        print(
            f"--mode {args.mode} but the key is a {actual}-mode key. Nothing was sent.",
            file=sys.stderr,
        )
        return 2
    if args.webhook_url and actual == "live" and not args.webhook_url.startswith("https://"):
        print("A live webhook URL must be https.", file=sys.stderr)
        return 2

    print(f"Stripe {actual} mode, {'APPLY' if args.apply else 'dry run'}")
    try:
        env = run(Stripe(key), apply=args.apply, webhook_url=args.webhook_url)
    except SetupError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 1
    if env:
        print("\nPaste into the environment file:")
        for name, value in env.items():
            print(f"{name}={value}")
        if "STRIPE_WEBHOOK_SECRET" in env:
            print("(the webhook secret is shown once; store it now)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
