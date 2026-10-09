# PayPal Sandbox validation

This checklist must be completed only with project-local/host environment variables. Never paste credentials into chat or commit `.env`.

1. Set `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, and `PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com`.
2. Start the app and confirm `/ready` reports both credentials configured without returning their values.
3. Submit the $24.50 scenario, approve the exact action, and create the order.
4. Follow the returned payer-action URL and sign in with a PayPal Sandbox personal test account.
5. Return to the app and capture.
6. Confirm a capture ID and deterministic receipt.
7. Reconcile; expect `MATCH`.
8. Execute the same request again; expect `ALREADY_EXECUTED` and no second capture.

Live evidence is not claimed until all eight steps are observed.
