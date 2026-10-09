# Publication and Render deployment

No external action has been performed.

## GitHub

Recommended repository: `https://github.com/chapaevv123/pulse-safe-commerce-agent`

From this project directory after reviewing the secret scan:

```powershell
git add .
git commit -m "Build Pulse Safe Commerce Agent"
git branch -M main
git remote add origin https://github.com/chapaevv123/pulse-safe-commerce-agent.git
git push -u origin main
```

Create the empty public repository first. Do not include `.env`.

## Render

1. Create a Blueprint or Web Service from the public repository; `render.yaml` selects Docker and `/health`.
2. Add server-side secrets `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET`.
3. Set `APP_BASE_URL` to the final Render origin.
4. Keep `PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com`.
5. Deploy, verify `/health` and `/ready`, then complete the Sandbox buyer-approval flow.

The free demo can run fixture AI mode without an external model key. For live AI interpretation, set `AI_PROVIDER=openai`, `OPENAI_API_KEY`, and—if needed—`OPENAI_BASE_URL`/`OPENAI_MODEL` server-side.
