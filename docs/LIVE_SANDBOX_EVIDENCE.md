# Real PayPal Sandbox validation evidence

Validated 2026-10-09 against `https://api-m.sandbox.paypal.com`. This is Sandbox evidence only; it is not a production or real-money validation.

- OAuth client-credentials token acquisition: PASS
- Existing buyer-approved Orders v2 order recovered: PASS
- Status before capture: `APPROVED`
- Capture: PASS
- Final order status: `COMPLETED`
- Amount/currency: `24.50 USD`
- PayPal order ID: `08V73608M0019794V`
- PayPal capture ID: `5ED43757PL303082Y`
- Exact consent binding: PASS
- Deterministic receipt matched PayPal order/capture/amount/currency: PASS
- Read-only reconciliation: `MATCH`
- Replay attempt: `ALREADY_EXECUTED`; remote capture count remained exactly one
- Real money: `0`

No credentials, access tokens, sandbox passwords, or protected response bodies are stored here.
