import hashlib
import hmac
import json


def canonical_payload(request_id: str, action: str, amount: str, currency: str, recipient: str, purpose: str) -> dict:
    return {"action": action, "amount": amount, "currency": currency, "purpose": purpose,
            "recipient_label": recipient, "request_id": request_id}


def stable_hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def secure_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)
