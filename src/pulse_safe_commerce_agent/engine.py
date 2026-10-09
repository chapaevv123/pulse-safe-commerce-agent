from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from .crypto import canonical_payload, secure_equal, stable_hash
from .models import CommerceIntent, Policy
from .paypal import PayPalClient, PayPalError, approve_link
from .policy import evaluate
from .store import Store

STAGES = ("INTENT", "PARSE", "POLICY", "APPROVAL", "PAYPAL_ORDER", "VERIFY_BINDING", "EXECUTE", "RECEIPT", "RECONCILE")


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class CommerceEngine:
    def __init__(self, store: Store, paypal: PayPalClient, interpreter, policy: Policy, app_base_url: str):
        self.store, self.paypal, self.interpreter, self.policy = store, paypal, interpreter, policy
        self.app_base_url = app_base_url.rstrip("/")

    async def propose(self, text: str) -> dict:
        request_id = "psc_" + uuid.uuid4().hex
        at = now()
        self.store.trace(request_id, "INTENT", "COMPLETE", text[:160], "Intent accepted", "INTENT_RECEIVED", at)
        intent = await self.interpreter.parse(text)
        payload = canonical_payload(request_id, intent.action, intent.amount, intent.currency, intent.recipient_label, intent.purpose)
        intent_hash = stable_hash(payload)
        result = evaluate(intent, self.policy)
        status = "AWAITING_APPROVAL" if result.allowed else "POLICY_BLOCKED"
        self.store.create({"request_id": request_id, "status": status, "intent": intent.public(), "intent_hash": intent_hash, "idempotency_key": "execute-" + request_id, "created_at": at})
        self.store.trace(request_id, "PARSE", "COMPLETE", f"{intent.amount} {intent.currency} to {intent.recipient_label}", "Canonical payment created", "PARSE_OK", at)
        self.store.trace(request_id, "POLICY", "PASS" if result.allowed else "BLOCKED", f"max={self.policy.max_single_payment}", result.explanation, result.reason_code, at)
        return self.view(request_id)

    def view(self, request_id: str) -> dict:
        row = self.store.get(request_id)
        if not row:
            raise KeyError(request_id)
        row["intent"] = json.loads(row.pop("intent_json"))
        row["receipt"] = json.loads(row["receipt_json"]) if row.get("receipt_json") else None
        row.pop("receipt_json", None)
        row["trace"] = self.store.traces(request_id)
        return row

    def approve(self, request_id: str) -> dict:
        row = self.store.get(request_id)
        if not row or row["status"] != "AWAITING_APPROVAL":
            raise ValueError("APPROVAL_NOT_ALLOWED")
        at = now()
        self.store.update(request_id, status="APPROVED", approval_hash=row["intent_hash"], approval_at=at, updated_at=at)
        self.store.trace(request_id, "APPROVAL", "APPROVED", "Exact canonical payload", "Owner approved exact action", "OWNER_APPROVED", at)
        return self.view(request_id)

    async def create_order(self, request_id: str) -> dict:
        row = self.store.get(request_id)
        if not row or row["status"] not in ("APPROVED", "PAYPAL_ORDER_CREATED"):
            raise ValueError("ORDER_CREATION_NOT_ALLOWED")
        if row.get("paypal_order_id"):
            return self.view(request_id)
        intent = json.loads(row["intent_json"])
        order = await self.paypal.create_order(intent["amount"], intent["currency"], request_id,
                                                f"{self.app_base_url}/api/payments/{request_id}/paypal-return",
                                                f"{self.app_base_url}/api/payments/{request_id}/paypal-cancel")
        at = now()
        self.store.update(request_id, status="PAYPAL_ORDER_CREATED", paypal_order_id=order["id"], paypal_status=order["status"], updated_at=at)
        self.store.trace(request_id, "PAYPAL_ORDER", "COMPLETE", order["id"], "Sandbox order created", "PAYPAL_ORDER_CREATED", at)
        result = self.view(request_id)
        result["approval_url"] = approve_link(order)
        return result

    async def execute(self, request_id: str, execution_override: dict | None = None) -> dict:
        row = self.store.get(request_id)
        if not row:
            raise KeyError(request_id)
        if row["status"] == "SUCCEEDED":
            return {**self.view(request_id), "replay": "IDEMPOTENT_NOOP", "reason_code": "ALREADY_EXECUTED"}
        if row["status"] != "PAYPAL_ORDER_CREATED":
            raise ValueError("EXECUTION_NOT_ALLOWED")
        intent = json.loads(row["intent_json"])
        payload = canonical_payload(request_id, intent["action"], intent["amount"], intent["currency"], intent["recipient_label"], intent["purpose"])
        if execution_override:
            payload.update(execution_override)
        actual_hash = stable_hash(payload)
        at = now()
        if not row["approval_hash"] or not secure_equal(actual_hash, row["approval_hash"]):
            self.store.update(request_id, status="BLOCKED", error_code="CONSENT_BINDING_MISMATCH", updated_at=at)
            self.store.trace(request_id, "VERIFY_BINDING", "BLOCKED", actual_hash, "Execution differs from approval", "CONSENT_BINDING_MISMATCH", at)
            return self.view(request_id)
        self.store.trace(request_id, "VERIFY_BINDING", "PASS", actual_hash, "Exact approval binding verified", "BINDING_MATCH", at)
        self.store.update(request_id, status="EXECUTING", updated_at=at)
        try:
            capture = await self.paypal.capture(row["paypal_order_id"], request_id)
        except PayPalError as exc:
            self.store.update(request_id, status="FAILED", error_code=exc.code, paypal_status="ERROR", updated_at=now())
            self.store.trace(request_id, "EXECUTE", "FAILED", row["paypal_order_id"], "PayPal returned an error", exc.code, now())
            return self.view(request_id)
        purchase = capture["purchase_units"][0]["payments"]["captures"][0]
        if purchase["amount"]["value"] != intent["amount"] or purchase["amount"]["currency_code"] != intent["currency"]:
            self.store.update(request_id, status="FAILED", error_code="PAYPAL_CAPTURE_MISMATCH", paypal_status=capture["status"], updated_at=now())
            return self.view(request_id)
        receipt = {"receipt_id": "receipt_" + stable_hash({"request_id": request_id, "capture": purchase["id"]})[:24],
                   "request_id": request_id, "intent_hash": row["intent_hash"], "approval_hash": row["approval_hash"],
                   "policy_result": "PASS", "paypal_order_id": row["paypal_order_id"], "paypal_capture_id": purchase["id"],
                   "amount": intent["amount"], "currency": intent["currency"], "execution_status": "SUCCEEDED",
                   "replay_protected": True, "created_at": now()}
        self.store.update(request_id, status="SUCCEEDED", paypal_capture_id=purchase["id"], paypal_status=capture["status"], receipt_json=json.dumps(receipt, sort_keys=True), updated_at=receipt["created_at"])
        self.store.trace(request_id, "EXECUTE", "SUCCEEDED", purchase["id"], "Sandbox capture verified", "PAYPAL_CAPTURED", receipt["created_at"])
        self.store.trace(request_id, "RECEIPT", "COMPLETE", receipt["receipt_id"], "Deterministic receipt stored", "RECEIPT_CREATED", receipt["created_at"])
        return self.view(request_id)

    async def reconcile(self, request_id: str) -> dict:
        row = self.store.get(request_id)
        if not row or not row.get("paypal_order_id"):
            return {"result": "UNKNOWN", "reason": "NO_PAYPAL_ORDER"}
        self.store.trace(request_id, "RECONCILE", "RUNNING", row["paypal_order_id"], "Querying PayPal Sandbox", "RECONCILING", now())
        try:
            remote = await self.paypal.get_order(row["paypal_order_id"])
        except PayPalError as exc:
            return {"result": "ERROR", "reason": exc.code}
        intent = json.loads(row["intent_json"])
        remote_amount = remote["purchase_units"][0]["amount"]
        match = remote_amount["value"] == intent["amount"] and remote_amount["currency_code"] == intent["currency"] and remote["id"] == row["paypal_order_id"]
        return {"result": "MATCH" if match else "MISMATCH", "local_status": row["status"], "paypal_status": remote["status"], "amount": remote_amount}
