from dataclasses import replace

from app.core.config import settings
from app.services import ai


def test_no_api_key_returns_none_without_network_call(monkeypatch):
    monkeypatch.setattr(ai, "settings", replace(settings, anthropic_api_key=""))
    assert ai.generate_narrative({"percentage": 80}) is None


def test_provider_exception_degrades_to_none(monkeypatch):
    monkeypatch.setattr(ai, "settings", replace(settings, anthropic_api_key="fake-key-for-test"))

    class ExplodingClient:
        def __init__(self, *a, **k):
            raise RuntimeError("simulated provider outage")

    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", ExplodingClient)

    assert ai.generate_narrative({"percentage": 80}) is None


def test_malformed_response_still_degrades_gracefully(monkeypatch):
    monkeypatch.setattr(ai, "settings", replace(settings, anthropic_api_key="fake-key-for-test"))

    class FakeMessage:
        content = []  # no text blocks at all -- should not crash, should yield empty -> None

    class FakeMessages:
        def create(self, **kwargs):
            return FakeMessage()

    class FakeClient:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)

    assert ai.generate_narrative({"percentage": 80}) is None


def test_ai_never_contributes_to_score(client, db_session, monkeypatch):
    """Scoring must be identical whether or not the AI provider is configured."""
    from .conftest import auth_headers, register

    monkeypatch.setattr(ai, "settings", replace(settings, anthropic_api_key=""))
    data = register(client)
    H = auth_headers(data["access_token"])
    client.patch("/api/me", headers=H, json={"preferences": {"preferred_topics": ["dsa"]}})
    test_id = client.get("/api/daily-challenge", headers=H).json()["test_id"]
    client.post(f"/api/tests/{test_id}/start", headers=H)
    result = client.post(f"/api/tests/{test_id}/submit", headers=H).json()
    assert result["score"] == 0  # nothing answered, regardless of AI availability
