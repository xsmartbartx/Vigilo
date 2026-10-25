from fastapi.testclient import TestClient

from vigilo_api.main import app

client = TestClient(app)


def test_healthz_returns_ok():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_reflects_brand_config():
    response = client.get("/version")
    assert response.status_code == 200
    body = response.json()
    assert body["product"] == "Vigilo"
    assert "api_version" in body
    assert "registry_version" in body


def test_version_reports_the_build_commit(monkeypatch):
    monkeypatch.setenv("GIT_SHA", "abc1234")
    assert client.get("/version").json()["commit"] == "abc1234"


def test_version_says_unknown_when_the_build_passed_no_commit(monkeypatch):
    monkeypatch.delenv("GIT_SHA", raising=False)
    assert client.get("/version").json()["commit"] == "unknown"
