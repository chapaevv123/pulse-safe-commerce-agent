# Security model

- Sandbox endpoint is enforced at startup. A live PayPal base URL raises an error.
- Credentials remain server-side environment variables and are never returned by readiness diagnostics.
- Money uses `Decimal`, normalized to two decimals.
- Policy precedes order creation and capture.
- Explicit approval stores a hash of request ID, action, amount, currency, recipient label, and purpose.
- The binding is recomputed immediately before capture.
- Successful actions are replay-safe locally; Orders requests also carry `PayPal-Request-Id`.
- The demo does not support arbitrary recipients, refunds, payouts, cards, wallets, or production money.
- Secure response headers are enabled. A production deployment should additionally use a durable managed database and per-user authenticated sessions before supporting multiple owners.
