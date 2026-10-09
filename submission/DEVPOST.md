# Project name

Pulse Safe Commerce Agent

## Elevator pitch

An AI commerce agent that can propose PayPal payments, but cannot execute them unless policy, explicit consent, exact action binding, and replay-safety checks all pass.

## Inspiration

Agentic commerce is usually presented as a straight line from recommendation to checkout. The risky part is the gap between an AI's interpretation and an irreversible money action. We built the trust layer for that gap.

## What it does

Pulse structures a natural-language purchase request, evaluates deterministic payment policy, requests owner approval, binds approval to the exact amount/currency/recipient/purpose/request, creates a PayPal Sandbox order, verifies the binding before capture, prevents duplicate execution, emits an auditable receipt, and reconciles local state against PayPal.

## How we built it

FastAPI orchestrates a nine-stage workflow backed by SQLite. A provider abstraction supports an OpenAI-compatible intent interpreter and a clearly labeled deterministic demo fixture. A policy engine uses Decimal money arithmetic. SHA-256 canonical action hashes bind consent. A server-only PayPal client uses OAuth and Orders v2 with `PayPal-Request-Id`. HTML/CSS/JavaScript presents the state machine and negative paths.

## How PayPal is used

PayPal Sandbox is the commerce execution system: OAuth authentication, order creation, buyer approval, capture, order retrieval, payment IDs, status, and remote reconciliation. Without PayPal, the app cannot execute or verify commerce.

## How AI is used

AI transforms free-form intent into a canonical commerce action and exposes confidence and assumptions. The agent then selects and sequences policy, consent, PayPal, verification, receipt, and reconciliation tools. AI never approves its own payment.

## Challenges

The hardest part was preserving useful autonomy while making the payment boundary deterministic. We separated probabilistic interpretation from deterministic authorization, handled browser-based sandbox approval honestly, and made replay and mutation failures judge-visible.

## Accomplishments

- Exact consent binding to six material action fields.
- Local and PayPal request idempotency.
- Five demonstrable positive/negative paths.
- Deterministic payment receipt and remote reconciliation.
- Server-only credentials and sandbox-only startup enforcement.
- A concise trace without hidden chain-of-thought.
- Real PayPal Sandbox validation of OAuth, buyer-approved Orders v2 capture, final status retrieval, receipt matching, reconciliation, and replay protection. The validated order remained at exactly one capture. No production endpoint or real money was used.

## What we learned

Agent safety improves when AI proposes and deterministic systems authorize. Payment correctness needs both local state and processor-side reconciliation. Negative paths are product features, not only tests.

## What's next

Add authenticated multi-owner sessions, PayPal webhooks, managed durable storage, richer budget policies, merchant allowlists, formal concurrency tests, and additional PayPal commerce primitives after security review.

## Built With

Python, FastAPI, PayPal REST API, PayPal Orders v2, SQLite, httpx, HTML, CSS, JavaScript, pytest, Docker, Render.

## Try it

- Live demo: `LIVE_DEMO_URL`
- Source: `PUBLIC_REPO_URL`
- Video: `YOUTUBE_URL`

## Judge instructions

Open the demo with no login. Start with the $24.50 scenario, then inspect the $120 policy block. Real capture requires the provided PayPal Sandbox test-account flow; full local setup is in the README. Fixture parsing is labeled `DEMO_FIXTURE`; PayPal results are labeled only when the live Sandbox API is used.

## Significant update disclosure

Safe Action MCP existed before the event and informed general safety patterns. New during this hackathon: the standalone PayPal Sandbox integration, commerce intent model, payment policies, exact payment consent binding, PayPal order/approval/capture flow, payment-specific idempotency, capture replay protection, PayPal reconciliation, commerce UI, receipt schema, and negative-path scenarios.
