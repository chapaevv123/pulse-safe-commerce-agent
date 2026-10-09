# Pulse Safe Commerce Agent

> AI can decide what it wants to buy. It should not be allowed to authorize its own payment.

Pulse Safe Commerce Agent is a deterministic safety boundary between AI commerce intent and PayPal Sandbox execution. It turns a natural-language request into a structured payment, evaluates policy, requires explicit owner consent bound to the exact action, uses PayPal Orders v2 for buyer-approved sandbox checkout and capture, prevents replay, emits a deterministic receipt, and reconciles local state against PayPal.

## Why it exists

Most commerce agents optimize discovery, recommendations, and checkout. They leave the dangerous gap between an agent's intent and money movement underspecified. Pulse focuses on trust between intent and payment.

## Why AI is load-bearing

The intent interpreter transforms free-form commerce requests into an actionable schema: action, amount, currency, recipient label, purpose, confidence, assumptions, and approval requirement. Remove it and users must manually construct payment objects; the agent workflow disappears. The public demo supports an OpenAI-compatible provider and an explicitly labeled deterministic fixture mode. Fixture output is never represented as a live AI result.

## Why PayPal is load-bearing

PayPal Sandbox provides OAuth, the Orders v2 commerce object, buyer approval, capture, remote status, and payment identifiers. Remove PayPal and the system can demonstrate policy, but cannot execute or reconcile commerce.

## Safety flow

```text
INTENT → PARSE → POLICY → APPROVAL → PAYPAL_ORDER
       → VERIFY_BINDING → EXECUTE → RECEIPT → RECONCILE
```

Generic agent: `intent → payment`

Pulse Safe Commerce: `intent → structured payment → policy → owner consent → exact binding → PayPal → receipt → reconciliation`

See [architecture](docs/ARCHITECTURE.md), [security](docs/SECURITY.md), and [live validation](docs/LIVE_VALIDATION.md).

## Verified Sandbox evidence

On 2026-10-09 the full PayPal Sandbox path passed: OAuth, Orders v2 creation, buyer approval, exactly-once capture, order retrieval, exact consent binding, deterministic receipt matching, replay blocking with one remote capture, and `MATCH` reconciliation. Amount: `24.50 USD`. This is Sandbox-only evidence; no production payment or real money was used. See [sanitized evidence](docs/LIVE_SANDBOX_EVIDENCE.md).

## PayPal endpoints

- `POST /v1/oauth2/token`
- `POST /v2/checkout/orders`
- `POST /v2/checkout/orders/{id}/capture`
- `GET /v2/checkout/orders/{id}`

All calls are server-side and hard-bound to `https://api-m.sandbox.paypal.com`.

## Agentic workflow

The agent interprets the request, selects a bounded PAY action, checks configured policy, pauses for consent, binds that consent to the canonical action, creates a PayPal order, verifies the binding again, captures only after sandbox buyer approval, generates a receipt, and compares local and PayPal state. Each stage records status, summary, decision, reason code, and timestamp.

## Setup

Requirements: Python 3.11+.

```powershell
cd C:\path\to\pulse-safe-commerce-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[test]"
Copy-Item .env.example .env
```

Set the sandbox credentials in `.env` locally. Never commit it.

`APP_BASE_URL` controls the PayPal buyer redirect origin. It defaults to
`http://localhost:8000` for local development. A public deployment must set it
to its HTTPS origin; Render uses `https://pulse-safe-commerce-agent.onrender.com`.
The application derives both `/api/payments/{request_id}/paypal-return` and
`/api/payments/{request_id}/paypal-cancel` from this value.

```powershell
uvicorn pulse_safe_commerce_agent.app:app --reload
pytest
```

Open `http://localhost:8000`. API documentation is at `/api/docs`; health is `/health`; readiness is `/ready`.

## Docker

```bash
docker build -t pulse-safe-commerce-agent .
docker run --env-file .env -p 8000:8000 pulse-safe-commerce-agent
```

## Judge flow

1. Run approved $24.50 payment with a $50 limit.
2. Observe structured intent, policy PASS, and exact owner approval.
3. Create a PayPal Sandbox order and approve it with a sandbox buyer account.
4. Capture and inspect the receipt.
5. Reconcile local and PayPal state.
6. Run the $120 policy block.
7. Use consent-mismatch and replay controls to prove negative paths.

## Demo scenarios

- Approved payment: $24.50 under a $50 maximum.
- Policy block: $120 exceeds the maximum; no PayPal call.
- Consent mismatch: approved $24.50, attempted $29.50; capture blocked.
- Replay: second execution returns `ALREADY_EXECUTED`; no duplicate capture.
- PayPal failure: errors are persisted and shown without fabricated success.

## Limitations

This is a hackathon sandbox prototype—not production payment infrastructure, financial advice, fraud prevention, or regulatory compliance. It supports a bounded merchant checkout flow, not arbitrary recipients. Fixture mode is deterministic demonstration data. SQLite is suitable for the demo; production would require managed durable storage, authentication, CSRF tokens tied to user sessions, webhooks, stronger concurrency controls, observability, and formal security review.

## Security

No live credentials, real money, wallet signing, arbitrary payout, or browser-side secret exists. `.env` and credential-like files are ignored. Readiness returns booleans only. See [SECURITY.md](docs/SECURITY.md).

## Significant update disclosure

Safe Action MCP predates this hackathon and taught general patterns: policy gates, explicit consent, action binding, replay safety, and receipts. This standalone project was newly built for the PayPal AI Hackathon: PayPal Sandbox OAuth and Orders v2, commerce-intent schema, payment-specific policy, exact payment consent binding, create/approve/capture workflow, PayPal request idempotency, replay prevention adapted to capture, remote reconciliation, PayPal-specific receipts, commerce UI, and five payment negative-path scenarios. No private Pulse runtime or Safe Action MCP source is required.

## License

MIT.
