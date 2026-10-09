from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

ALLOWED_STATES = {"PROPOSED", "POLICY_BLOCKED", "AWAITING_APPROVAL", "APPROVED", "PAYPAL_ORDER_CREATED", "EXECUTING", "SUCCEEDED", "FAILED", "BLOCKED", "RECONCILING"}


def money(value: Any) -> str:
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise ValueError("Invalid money amount")
    if amount <= 0:
        raise ValueError("Amount must be positive")
    return format(amount, ".2f")


@dataclass(frozen=True)
class CommerceIntent:
    action: str
    amount: str
    currency: str
    recipient_label: str
    purpose: str
    confidence: float
    assumptions: list[str] = field(default_factory=list)
    requires_owner_approval: bool = True
    provider: str = "fixture"

    def __post_init__(self):
        object.__setattr__(self, "amount", money(self.amount))
        object.__setattr__(self, "currency", self.currency.upper())
        if self.action != "PAY":
            raise ValueError("Only PAY actions are supported")

    def public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Policy:
    max_single_payment: str = "50.00"
    allowed_currencies: tuple[str, ...] = ("USD",)
    approval_required: bool = True
    allowed_purposes: tuple[str, ...] = ()
    recipient_allowlist: tuple[str, ...] = ()
    daily_limit: str | None = None


@dataclass(frozen=True)
class PolicyResult:
    allowed: bool
    reason_code: str
    explanation: str
