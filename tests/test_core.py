import asyncio
import json
import re
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from pulse_safe_commerce_agent.app import create_app
from pulse_safe_commerce_agent.config import SANDBOX_URL, Settings
from pulse_safe_commerce_agent.crypto import canonical_payload, secure_equal, stable_hash
from pulse_safe_commerce_agent.engine import CommerceEngine
from pulse_safe_commerce_agent.intent import AIProviderUnavailable, FixtureInterpreter, OpenAICompatibleInterpreter
from pulse_safe_commerce_agent.models import CommerceIntent, Policy, money
from pulse_safe_commerce_agent.paypal import PayPalClient, PayPalError, approve_link
from pulse_safe_commerce_agent.policy import evaluate
from pulse_safe_commerce_agent.store import Store


class FakePayPal:
    def __init__(self, fail=False, mismatch=False): self.fail, self.mismatch, self.captures, self.urls = fail, mismatch, 0, None
    async def create_order(self, amount, currency, request_id, return_url, cancel_url):
        self.urls = (return_url, cancel_url)
        return {"id": "ORDER-1", "status": "PAYER_ACTION_REQUIRED", "links": [{"rel": "payer-action", "href": "https://www.sandbox.paypal.com/checkoutnow?token=ORDER-1"}]}
    async def capture(self, order_id, request_id):
        self.captures += 1
        if self.fail: raise PayPalError("INSTRUMENT_DECLINED", 422)
        amount = "99.00" if self.mismatch else "24.50"
        return {"id": order_id, "status": "COMPLETED", "purchase_units": [{"payments": {"captures": [{"id": "CAP-1", "amount": {"value": amount, "currency_code": "USD"}}]}}]}
    async def get_order(self, order_id):
        amount = "99.00" if self.mismatch else "24.50"
        return {"id": order_id, "status": "COMPLETED", "purchase_units": [{"amount": {"value": amount, "currency_code": "USD"}}]}


def engine(paypal=None):
    return CommerceEngine(Store(":memory:"), paypal or FakePayPal(), FixtureInterpreter(), Policy(), "http://test")


async def approved(e):
    p = await e.propose("Pay $24.50 for the research report.")
    e.approve(p["request_id"])
    await e.create_order(p["request_id"])
    return p["request_id"]


def test_money_decimal(): assert money("24.5") == "24.50"
def test_money_rejects_zero():
    with pytest.raises(ValueError): money("0")
def test_intent_schema(): assert CommerceIntent("PAY", "1", "usd", "x", "y", .8).currency == "USD"
def test_intent_rejects_nonpay():
    with pytest.raises(ValueError): CommerceIntent("REFUND", "1", "USD", "x", "y", .8)
def test_fixture_parse(): assert asyncio.run(FixtureInterpreter().parse("Pay $24.50 for the research report.")).provider == "DEMO_FIXTURE"
def test_fixture_needs_amount():
    with pytest.raises(ValueError): asyncio.run(FixtureInterpreter().parse("Pay for this report"))
def test_ai_unavailable_explicit():
    with pytest.raises(AIProviderUnavailable): OpenAICompatibleInterpreter("", "http://x", "m")
def test_policy_allow(): assert evaluate(CommerceIntent("PAY", "24.50", "USD", "x", "y", .8), Policy()).allowed
def test_policy_block(): assert evaluate(CommerceIntent("PAY", "120", "USD", "x", "y", .8), Policy()).reason_code == "POLICY_LIMIT_EXCEEDED"
def test_currency_block(): assert evaluate(CommerceIntent("PAY", "2", "EUR", "x", "y", .8), Policy()).reason_code == "CURRENCY_NOT_ALLOWED"
def test_daily_limit(): assert evaluate(CommerceIntent("PAY", "25", "USD", "x", "y", .8), Policy(daily_limit="30"), "10").reason_code == "DAILY_LIMIT_EXCEEDED"
def test_hash_deterministic(): assert stable_hash({"b": 2, "a": 1}) == stable_hash({"a": 1, "b": 2})
def test_hash_material_change(): assert stable_hash({"a": 1}) != stable_hash({"a": 2})
def test_secure_equal(): assert secure_equal("abc", "abc") and not secure_equal("abc", "abd")
def test_approval_required(): assert asyncio.run(engine().propose("Pay $24.50 for the research report."))["status"] == "AWAITING_APPROVAL"
def test_policy_block_no_paypal(): assert asyncio.run(engine().propose("Pay $120 for the research report."))["status"] == "POLICY_BLOCKED"
def test_approval_binding():
    e=engine(); rid=asyncio.run(e.propose("Pay $24.50 for the research report."))["request_id"]; assert e.approve(rid)["approval_hash"]
def test_binding_mismatch_blocks():
    e=engine(); rid=asyncio.run(approved(e)); result=asyncio.run(e.execute(rid,{"amount":"29.50"})); assert result["error_code"]=="CONSENT_BINDING_MISMATCH"
def test_success_receipt():
    e=engine(); rid=asyncio.run(approved(e)); result=asyncio.run(e.execute(rid)); assert result["receipt"]["execution_status"]=="SUCCEEDED"
def test_replay_no_second_capture():
    pp=FakePayPal(); e=engine(pp); rid=asyncio.run(approved(e)); asyncio.run(e.execute(rid)); result=asyncio.run(e.execute(rid)); assert result["reason_code"]=="ALREADY_EXECUTED" and pp.captures==1
def test_paypal_failure():
    e=engine(FakePayPal(fail=True)); rid=asyncio.run(approved(e)); assert asyncio.run(e.execute(rid))["status"]=="FAILED"
def test_capture_mismatch():
    e=engine(FakePayPal(mismatch=True)); rid=asyncio.run(approved(e)); assert asyncio.run(e.execute(rid))["error_code"]=="PAYPAL_CAPTURE_MISMATCH"
def test_reconcile_match():
    e=engine(); rid=asyncio.run(approved(e)); assert asyncio.run(e.reconcile(rid))["result"]=="MATCH"
def test_reconcile_mismatch():
    e=engine(FakePayPal(mismatch=True)); rid=asyncio.run(approved(e)); assert asyncio.run(e.reconcile(rid))["result"]=="MISMATCH"
def test_receipt_determinism():
    e=engine(); rid=asyncio.run(approved(e)); receipt=asyncio.run(e.execute(rid))["receipt"]; assert receipt["receipt_id"].startswith("receipt_")
def test_create_order_idempotent():
    pp=FakePayPal(); e=engine(pp); rid=asyncio.run(approved(e)); first=asyncio.run(e.create_order(rid)); assert first["paypal_order_id"]=="ORDER-1"
def test_local_paypal_redirect_urls():
    pp=FakePayPal(); e=engine(pp); rid=asyncio.run(approved(e)); assert pp.urls == (f"http://test/api/payments/{rid}/paypal-return", f"http://test/api/payments/{rid}/paypal-cancel")
def test_default_app_base_url_is_localhost(): assert Settings().app_base_url == "http://localhost:8000"
def test_render_paypal_redirect_urls():
    pp=FakePayPal(); e=CommerceEngine(Store(":memory:"), pp, FixtureInterpreter(), Policy(), "https://pulse-safe-commerce-agent.onrender.com/"); rid=asyncio.run(approved(e)); assert pp.urls == (f"https://pulse-safe-commerce-agent.onrender.com/api/payments/{rid}/paypal-return", f"https://pulse-safe-commerce-agent.onrender.com/api/payments/{rid}/paypal-cancel")
def test_cancel_route_does_not_capture():
    pp=FakePayPal(); c=TestClient(create_app(Settings(database_path=":memory:"), Store(":memory:"), pp, FixtureInterpreter())); proposed=c.post("/api/intents",json={"text":"Pay $24.50 for the research report."}).json(); result=c.get(f"/api/payments/{proposed['request_id']}/paypal-cancel").json(); assert result["paypal_cancelled"] is True and pp.captures==0
def test_approve_link(): assert approve_link({"links":[{"rel":"approve","href":"x"}]})=="x"
def test_live_base_rejected():
    with pytest.raises(ValueError): Settings(paypal_base_url="https://api-m.paypal.com").validate()
def test_health_and_readiness():
    c=TestClient(create_app(Settings(database_path=":memory:"), Store(":memory:"), FakePayPal(), FixtureInterpreter())); assert c.get("/health").json()=={"status":"ok","paypal":"sandbox","mode":"safe-commerce"}; assert "paypal_client_secret_configured" in c.get("/ready").json()
def test_api_policy_block():
    c=TestClient(create_app(Settings(database_path=":memory:"), Store(":memory:"), FakePayPal(), FixtureInterpreter())); assert c.post("/api/intents",json={"text":"Pay $120 for the research report.","max_single_payment":"50"}).json()["status"]=="POLICY_BLOCKED"
def test_security_headers():
    c=TestClient(create_app(Settings(database_path=":memory:"), Store(":memory:"), FakePayPal(), FixtureInterpreter())); assert c.get("/").headers["x-frame-options"]=="DENY"
def test_no_secrets_in_public_files():
    root=Path(__file__).parents[1]
    for path in root.rglob("*"):
        if path.is_file() and path.name != "test_core.py" and path.suffix in {".py",".md",".html",".js",".css",".yaml",".toml"}:
            text=path.read_text("utf-8",errors="ignore")
            assert not re.search(r"PAYPAL_CLIENT_SECRET\s*=\s*[A-Za-z0-9_-]{20,}", text)
