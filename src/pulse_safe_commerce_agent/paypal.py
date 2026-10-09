from __future__ import annotations

import base64
from typing import Any

import httpx

from .config import SANDBOX_URL, Settings


class PayPalError(RuntimeError):
    def __init__(self, code: str, status: int = 0):
        super().__init__(code)
        self.code, self.status = code, status


class PayPalClient:
    def __init__(self, settings: Settings, transport=None):
        settings.validate()
        self.settings, self.transport = settings, transport

    async def _token(self) -> str:
        if not self.settings.paypal_ready:
            raise PayPalError("PAYPAL_CREDENTIALS_UNAVAILABLE")
        basic = base64.b64encode(f"{self.settings.paypal_client_id}:{self.settings.paypal_client_secret}".encode()).decode()
        async with httpx.AsyncClient(timeout=20, transport=self.transport) as client:
            res = await client.post(SANDBOX_URL + "/v1/oauth2/token", headers={"Authorization": "Basic " + basic, "Accept": "application/json"}, data={"grant_type": "client_credentials"})
        if res.status_code != 200:
            try:
                error = res.json()
                safe_code = str(error.get("error") or error.get("name") or "PAYPAL_AUTH_FAILED")
            except ValueError:
                safe_code = "PAYPAL_AUTH_FAILED"
            raise PayPalError(safe_code, res.status_code)
        return res.json()["access_token"]

    async def _request(self, method: str, path: str, request_id: str | None = None, payload: dict | None = None) -> dict[str, Any]:
        token = await self._token()
        headers = {"Authorization": "Bearer " + token, "Accept": "application/json", "Content-Type": "application/json", "Prefer": "return=representation"}
        if request_id:
            headers["PayPal-Request-Id"] = request_id[:108]
        async with httpx.AsyncClient(timeout=25, transport=self.transport) as client:
            res = await client.request(method, SANDBOX_URL + path, headers=headers, json=payload)
        if res.status_code not in (200, 201):
            code = res.json().get("name", "PAYPAL_API_ERROR") if res.content else "PAYPAL_API_ERROR"
            raise PayPalError(code, res.status_code)
        return res.json()

    async def create_order(self, amount: str, currency: str, request_id: str, return_url: str, cancel_url: str) -> dict:
        payload = {"intent": "CAPTURE", "purchase_units": [{"reference_id": request_id, "description": "Pulse Safe Commerce approved payment", "amount": {"currency_code": currency, "value": amount}}],
                   "payment_source": {"paypal": {"experience_context": {"return_url": return_url, "cancel_url": cancel_url, "user_action": "PAY_NOW", "shipping_preference": "NO_SHIPPING"}}}}
        return await self._request("POST", "/v2/checkout/orders", "create-" + request_id, payload)

    async def capture(self, order_id: str, request_id: str) -> dict:
        return await self._request("POST", f"/v2/checkout/orders/{order_id}/capture", "capture-" + request_id, {})

    async def get_order(self, order_id: str) -> dict:
        return await self._request("GET", f"/v2/checkout/orders/{order_id}")


def approve_link(order: dict) -> str | None:
    return next((x.get("href") for x in order.get("links", []) if x.get("rel") in ("payer-action", "approve")), None)
