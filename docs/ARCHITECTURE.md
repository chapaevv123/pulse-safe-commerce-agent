# Architecture

```text
Natural-language commerce intent
        │
        ▼
AI/fixture interpreter ──► canonical payment intent
        │
        ▼
Policy gate ──BLOCK──► no PayPal call
        │ PASS
        ▼
Owner approval → SHA-256 exact-action binding
        │
        ▼
PayPal Sandbox Orders v2 create → buyer sandbox approval
        │
        ▼
Binding verification → capture with PayPal-Request-Id
        │
        ▼
Deterministic receipt → PayPal read-only reconciliation
```

The browser never receives PayPal credentials. The server accepts only a bounded PAY action, USD by default, and a configured sandbox merchant. Local status and a unique idempotency key prevent a successful request from reaching capture twice. PayPal's request ID adds transport-level idempotency.

The agent trace exposes concise stage inputs, decisions, reason codes, and timestamps. It does not expose hidden chain-of-thought.
