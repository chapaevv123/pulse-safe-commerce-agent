# Demo video script — 110 seconds

**0–10s — Problem**  
“AI can propose what to buy. It should not be allowed to authorize its own payment. Pulse Safe Commerce Agent places a deterministic safety boundary between agent intent and PayPal.”

**10–25s — Intent**  
Enter: “Pay $24.50 for the research report.” Show the agent convert it into amount, currency, recipient label, purpose, confidence, and assumptions.

**25–40s — Policy**  
Show the $50 maximum and `POLICY_PASS`. Explain that policy runs before PayPal.

**40–52s — Consent**  
Approve the exact payment. Show the approval hash binding request ID, action, amount, currency, recipient, and purpose.

**52–75s — PayPal**  
Create a LIVE SANDBOX order, follow PayPal buyer approval, then capture. State clearly: sandbox only, no real money.

**75–88s — Receipt and reconciliation**  
Show PayPal order/capture IDs, deterministic receipt, and `MATCH` reconciliation.

**88–100s — Negative path**  
Run $120 against the $50 policy. Show `POLICY_LIMIT_EXCEEDED` and no PayPal call.

**100–108s — Binding and replay**  
Show a $29.50 mutation blocked by `CONSENT_BINDING_MISMATCH`, then replay returns `ALREADY_EXECUTED` with no second capture.

**108–110s — Close**  
“This is trust between AI intent and payment—not autonomy without control.”

Recording notes: keep under three minutes; show functioning UI; use no music or third-party copyrighted material; obscure sandbox test-account credentials.
