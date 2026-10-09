from decimal import Decimal

from .models import CommerceIntent, Policy, PolicyResult


def evaluate(intent: CommerceIntent, policy: Policy, spent_today: str = "0.00") -> PolicyResult:
    if intent.currency not in policy.allowed_currencies:
        return PolicyResult(False, "CURRENCY_NOT_ALLOWED", "Currency is outside policy.")
    if Decimal(intent.amount) > Decimal(policy.max_single_payment):
        return PolicyResult(False, "POLICY_LIMIT_EXCEEDED", "Payment exceeds the single-payment limit.")
    if policy.allowed_purposes and intent.purpose not in policy.allowed_purposes:
        return PolicyResult(False, "PURPOSE_NOT_ALLOWED", "Purpose is outside policy.")
    if policy.recipient_allowlist and intent.recipient_label not in policy.recipient_allowlist:
        return PolicyResult(False, "RECIPIENT_NOT_ALLOWED", "Recipient is outside policy.")
    if policy.daily_limit and Decimal(spent_today) + Decimal(intent.amount) > Decimal(policy.daily_limit):
        return PolicyResult(False, "DAILY_LIMIT_EXCEEDED", "Payment exceeds the daily limit.")
    return PolicyResult(True, "POLICY_PASS", "All configured policy checks passed.")
