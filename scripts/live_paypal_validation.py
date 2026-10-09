"""Two-phase real PayPal Sandbox validation; never logs credentials or access tokens."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

from pulse_safe_commerce_agent.config import Settings
from pulse_safe_commerce_agent.engine import CommerceEngine
from pulse_safe_commerce_agent.intent import FixtureInterpreter
from pulse_safe_commerce_agent.models import Policy
from pulse_safe_commerce_agent.paypal import PayPalClient
from pulse_safe_commerce_agent.paypal import PayPalError
from pulse_safe_commerce_agent.store import Store

ROOT = Path(__file__).parents[1]
STATE = ROOT / ".paypal_live_validation_state.json"
DB = ROOT / "live_validation.db"


def write_state(value: dict) -> None:
    STATE.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def read_state() -> dict:
    if not STATE.exists():
        raise RuntimeError("No live validation state. Run --phase create first.")
    return json.loads(STATE.read_text(encoding="utf-8"))


def setup():
    load_dotenv(ROOT / ".env", override=True)
    settings = Settings.from_env()
    settings.validate()
    if not settings.paypal_ready:
        raise RuntimeError("PayPal Sandbox credentials are not configured")
    store = Store(str(DB))
    paypal = PayPalClient(settings)
    engine = CommerceEngine(store, paypal, FixtureInterpreter(), Policy(max_single_payment="50.00"), settings.app_base_url)
    return engine, paypal


async def create() -> None:
    engine, _ = setup()
    proposed = await engine.propose("Pay $24.50 for the research report.")
    approved = engine.approve(proposed["request_id"])
    order = await engine.create_order(proposed["request_id"])
    state = {"request_id": proposed["request_id"], "paypal_order_id": order["paypal_order_id"],
             "intent_hash": approved["intent_hash"], "approval_hash": approved["approval_hash"]}
    write_state(state)
    print(json.dumps({"oauth": "PASS", "order_created": "PASS", "request_id": state["request_id"],
                      "paypal_order_id": state["paypal_order_id"], "buyer_approval": "OWNER_ACTION_REQUIRED",
                      "approval_url": order.get("approval_url"), "amount": "24.50", "currency": "USD",
                      "sandbox_only": True}, indent=2))


async def complete() -> None:
    engine, paypal = setup()
    state = read_state()
    before = await paypal.get_order(state["paypal_order_id"])
    if before.get("status") != "APPROVED":
        approve = next((x.get("href") for x in before.get("links", []) if x.get("rel") in ("payer-action", "approve")), None)
        print(json.dumps({"buyer_approval": "OWNER_ACTION_REQUIRED", "paypal_status": before.get("status"),
                          "approval_url": approve, "sandbox_only": True}, indent=2))
        return
    local_before = engine.view(state["request_id"])
    binding_valid = local_before["intent_hash"] == local_before["approval_hash"] == state["approval_hash"]
    captured = await engine.execute(state["request_id"])
    remote = await paypal.get_order(state["paypal_order_id"])
    replay = await engine.execute(state["request_id"])
    reconciliation = await engine.reconcile(state["request_id"])
    receipt = captured.get("receipt") or {}
    captures = remote.get("purchase_units", [{}])[0].get("payments", {}).get("captures", [])
    capture = captures[0] if captures else {}
    receipt_match = bool(receipt) and receipt.get("paypal_order_id") == remote.get("id") and receipt.get("paypal_capture_id") == capture.get("id") and receipt.get("amount") == capture.get("amount", {}).get("value") and receipt.get("currency") == capture.get("amount", {}).get("currency_code")
    result = {"oauth": "PASS", "order_created": "PASS", "buyer_approval": "PASS",
              "capture": "PASS" if captured.get("status") == "SUCCEEDED" else "FAIL",
              "status_retrieval": "PASS", "paypal_status": remote.get("status"),
              "receipt_match": "PASS" if receipt_match else "FAIL",
              "consent_binding": "PASS" if binding_valid else "FAIL",
              "replay_block": "PASS" if replay.get("reason_code") == "ALREADY_EXECUTED" and len(captures) == 1 else "FAIL",
              "reconciliation": reconciliation.get("result"), "paypal_order_id": remote.get("id"),
              "paypal_capture_id": capture.get("id"), "capture_count": len(captures), "sandbox_only": True,
              "real_money": 0}
    write_state({**state, **{k: v for k, v in result.items() if k not in ("approval_url",)}})
    print(json.dumps(result, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("create", "complete"), required=True)
    args = parser.parse_args()
    try:
        asyncio.run(create() if args.phase == "create" else complete())
    except PayPalError as exc:
        print(json.dumps({"result": "FAIL", "stage": "OAUTH_OR_PAYPAL_API", "http_status": exc.status,
                          "paypal_error": exc.code, "sandbox_only": True, "real_money": 0}, indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
