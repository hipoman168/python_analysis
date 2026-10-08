"""Offline L5 contract tests; do not count as cross-center E2E acceptance."""
from fastapi.testclient import TestClient
from dayong_l5_gateway.app_v2 import app
import dayong_l5_gateway.app_v2 as gateway

client = TestClient(app)

def test_health_reports_unconfigured_without_db(monkeypatch):
    monkeypatch.setattr(gateway, "DATABASE_URL", "")
    monkeypatch.setattr(gateway, "AGENT_KEYS_JSON", "{}")
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["configured"] is False

def test_inbox_requires_agent_credential(monkeypatch):
    monkeypatch.setattr(gateway, "AGENT_KEYS_JSON", '{"MOON-INTERIOR":"test-secret"}')
    assert client.get("/v1/messages").status_code == 401
    assert client.get("/v1/messages",headers={"Authorization":"Bearer invalid"}).status_code == 401

def test_authenticated_inbox_refuses_without_durable_database(monkeypatch):
    monkeypatch.setattr(gateway, "DATABASE_URL", "")
    monkeypatch.setattr(gateway, "AGENT_KEYS_JSON", '{"MOON-INTERIOR":"test-secret"}')
    r=client.get("/v1/messages",headers={"Authorization":"Bearer test-secret"})
    assert r.status_code == 503

def test_reply_requires_ack_and_identity(monkeypatch):
    monkeypatch.setattr(gateway, "AGENT_KEYS_JSON", '{"MOON-INTERIOR":"test-secret"}')
    assert client.post("/v1/messages/00000000-0000-0000-0000-000000000001/reply",json={"payload":{"ok":True}}).status_code == 401
