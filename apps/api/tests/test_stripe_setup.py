"""scripts/stripe_setup.py against an in-memory fake of the Stripe endpoints it uses."""

import importlib.util
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

_spec = importlib.util.spec_from_file_location(
    "stripe_setup", Path(__file__).parents[3] / "scripts" / "stripe_setup.py"
)
setup = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(setup)


class FakeStripe:
    def __init__(self):
        self.products, self.prices, self.portals, self.hooks = [], [], [], []
        self.posts: list[tuple[str, dict]] = []
        self.gets = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path.removeprefix("/v1")
        if request.method == "GET":
            self.gets += 1
            if path == "/prices":
                keys = request.url.params.get_list("lookup_keys[]")
                data = [p for p in self.prices if p["lookup_key"] in keys]
            else:
                data = {
                    "/products": self.products,
                    "/billing_portal/configurations": self.portals,
                    "/webhook_endpoints": self.hooks,
                }[path]
            return httpx.Response(200, json={"data": data})
        form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        self.posts.append((path, form))
        n = len(self.posts)
        if path == "/products":
            obj = {"id": f"prod_{n}", "metadata": {"vigilo": form["metadata[vigilo]"]}}
            self.products.append(obj)
        elif path == "/prices":
            obj = {
                "id": f"price_{n}",
                "lookup_key": form["lookup_key"],
                "unit_amount": int(form["unit_amount"]),
                "currency": form["currency"],
            }
            self.prices.append(obj)
        elif path == "/billing_portal/configurations":
            obj = {"id": f"bpc_{n}", "metadata": {"vigilo": "portal"}}
            self.portals.append(obj)
        else:
            obj = {"id": f"we_{n}", "url": form["url"], "secret": "whsec_fake"}
            self.hooks.append(obj)
        return httpx.Response(200, json=obj)


def _stripe(fake: FakeStripe) -> "setup.Stripe":
    return setup.Stripe("sk_test_x", transport=httpx.MockTransport(fake.handler))


def test_a_dry_run_only_reads():
    fake = FakeStripe()
    env = setup.run(
        _stripe(fake), apply=False, webhook_url="https://x.test/hook", out=lambda *_: None
    )
    assert fake.posts == [] and env == {}


def test_apply_creates_everything_with_the_apps_prices():
    fake = FakeStripe()
    env = setup.run(
        _stripe(fake), apply=True, webhook_url="https://x.test/hook", out=lambda *_: None
    )
    assert set(env) == {
        "STRIPE_PRICE_ID_PRO",
        "STRIPE_PRICE_ID_PRO_YEARLY",
        "STRIPE_PORTAL_CONFIGURATION_ID",
        "STRIPE_WEBHOOK_SECRET",
    }
    amounts = {p["lookup_key"]: p["unit_amount"] for p in fake.prices}
    assert amounts == {"vigilo_pro_monthly": 2900, "vigilo_pro_yearly": 29000}
    portal = dict(fake.posts)["/billing_portal/configurations"]
    assert portal["features[subscription_cancel][mode]"] == "at_period_end"
    assert (
        portal["features[subscription_update][products][0][prices][1]"]
        == env["STRIPE_PRICE_ID_PRO_YEARLY"]
    )
    hook = dict(fake.posts)["/webhook_endpoints"]
    assert "invoice.payment_failed" in hook.values()


def test_a_second_run_creates_nothing():
    fake = FakeStripe()
    setup.run(_stripe(fake), apply=True, webhook_url="https://x.test/hook", out=lambda *_: None)
    posts_before = len(fake.posts)
    env = setup.run(
        _stripe(fake), apply=True, webhook_url="https://x.test/hook", out=lambda *_: None
    )
    assert len(fake.posts) == posts_before
    assert "STRIPE_WEBHOOK_SECRET" not in env  # Stripe never shows it again
    assert env["STRIPE_PRICE_ID_PRO"] == fake.prices[0]["id"]


def test_a_price_with_the_wrong_amount_stops_the_run():
    fake = FakeStripe()
    fake.products.append({"id": "prod_x", "metadata": {"vigilo": "pro"}})
    fake.prices.append(
        {
            "id": "price_old",
            "lookup_key": "vigilo_pro_monthly",
            "unit_amount": 1900,
            "currency": "usd",
        }
    )
    with pytest.raises(setup.SetupError, match="archive it"):
        setup.run(_stripe(fake), apply=True, webhook_url=None, out=lambda *_: None)
    assert fake.posts == []


def test_a_mode_that_does_not_match_the_key_sends_nothing(monkeypatch, capsys):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_" + "a" * 30)
    called = []
    monkeypatch.setattr(setup, "run", lambda *a, **k: called.append(1))
    assert setup.main(["--mode", "test"]) == 2
    assert called == []
    err = capsys.readouterr().err
    assert "live-mode key" in err and "sk_live" not in err


def test_a_missing_or_unrecognised_key_is_refused(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    assert setup.main(["--mode", "test"]) == 2
    monkeypatch.setenv("STRIPE_SECRET_KEY", "not-a-key")
    assert setup.main(["--mode", "test"]) == 2


def test_a_same_named_product_without_the_marker_stops_the_script_instead_of_duplicating(capsys):
    fake = FakeStripe()
    fake.products.append({"id": "prod_old", "name": "Vigilo Pro", "metadata": {}})
    stripe = setup.Stripe("sk_test_x", transport=httpx.MockTransport(fake.handler))

    with pytest.raises(setup.SetupError, match="prod_old"):
        setup.run(stripe, apply=True, webhook_url=None)

    assert fake.posts == []  # nothing was created


def test_a_marked_product_on_a_later_page_is_found_instead_of_creating_another():
    pages = {
        None: {"data": [{"id": f"prod_{i}", "metadata": {}} for i in range(100)], "has_more": True},
        "prod_99": {
            "data": [{"id": "prod_late", "metadata": {"vigilo": "pro"}}],
            "has_more": False,
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        return httpx.Response(200, json=pages[request.url.params.get("starting_after")])

    stripe = setup.Stripe("sk_test_x", transport=httpx.MockTransport(handler))

    assert setup.find_product(stripe)["id"] == "prod_late"
