from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .config import Settings
from .engine import CommerceEngine, now
from .intent import FixtureInterpreter, OpenAICompatibleInterpreter
from .models import Policy
from .paypal import PayPalClient
from .store import Store

load_dotenv()
ROOT = Path(__file__).parent


class IntentBody(BaseModel):
    text: str = Field(min_length=5, max_length=500)
    max_single_payment: str = "50.00"


class ExecuteBody(BaseModel):
    amount_override: str | None = None


def create_app(settings: Settings | None = None, store: Store | None = None, paypal=None, interpreter=None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.validate()
    store = store or Store(settings.database_path)
    paypal = paypal or PayPalClient(settings)
    if interpreter is None:
        interpreter = (OpenAICompatibleInterpreter(settings.openai_api_key, settings.openai_base_url, settings.openai_model)
                       if settings.ai_provider == "openai" else FixtureInterpreter())
    app = FastAPI(title="Pulse Safe Commerce Agent", version="0.1.0", docs_url="/api/docs")
    app.state.settings, app.state.store = settings, store
    app.state.engine = CommerceEngine(store, paypal, interpreter, Policy(), settings.app_base_url)
    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
    templates = Jinja2Templates(directory=ROOT / "templates")

    @app.middleware("http")
    async def headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'"
        return response

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        return templates.TemplateResponse(request, "index.html", {"paypal_ready": settings.paypal_ready, "ai_provider": settings.ai_provider})

    @app.get("/health")
    async def health():
        return {"status": "ok", "paypal": "sandbox", "mode": "safe-commerce"}

    @app.get("/ready")
    async def ready():
        return {"status": "ready" if settings.paypal_ready else "configuration_required", "paypal_client_id_configured": bool(settings.paypal_client_id), "paypal_client_secret_configured": bool(settings.paypal_client_secret), "paypal_base_url": "sandbox"}

    @app.post("/api/intents")
    async def propose(body: IntentBody):
        app.state.engine.policy = Policy(max_single_payment=body.max_single_payment)
        try:
            return await app.state.engine.propose(body.text)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(422, detail=str(exc))

    @app.get("/api/payments/{request_id}")
    async def payment(request_id: str):
        try:
            return app.state.engine.view(request_id)
        except KeyError:
            raise HTTPException(404, "Not found")

    @app.post("/api/payments/{request_id}/approve")
    async def approve(request_id: str):
        try:
            return app.state.engine.approve(request_id)
        except (KeyError, ValueError) as exc:
            raise HTTPException(409, detail=str(exc))

    @app.post("/api/payments/{request_id}/paypal-order")
    async def order(request_id: str):
        try:
            return await app.state.engine.create_order(request_id)
        except Exception as exc:
            raise HTTPException(409, detail=getattr(exc, "code", str(exc)))

    @app.get("/api/payments/{request_id}/paypal-return")
    async def paypal_return(request_id: str):
        try:
            result = await app.state.engine.execute(request_id)
            if result.get("status") == "SUCCEEDED":
                await app.state.engine.reconcile(request_id)
                return RedirectResponse(f"/?request_id={request_id}&payment=success", status_code=303)
            return RedirectResponse(f"/?request_id={request_id}&payment=error", status_code=303)
        except Exception as exc:
            if app.state.store.get(request_id):
                code = str(getattr(exc, "code", "PAYPAL_RETURN_FAILED"))[:80]
                app.state.store.update(request_id, status="FAILED", error_code=code, updated_at=now())
            return RedirectResponse(f"/?request_id={request_id}&payment=error", status_code=303)

    @app.get("/api/payments/{request_id}/paypal-cancel")
    async def paypal_cancel(request_id: str):
        try:
            app.state.engine.view(request_id)
        except KeyError:
            raise HTTPException(404, "Not found")
        return RedirectResponse(f"/?request_id={request_id}&payment=cancelled", status_code=303)

    @app.post("/api/payments/{request_id}/execute")
    async def execute(request_id: str, body: ExecuteBody):
        override = {"amount": body.amount_override} if body.amount_override else None
        try:
            return await app.state.engine.execute(request_id, override)
        except (KeyError, ValueError) as exc:
            raise HTTPException(409, detail=str(exc))

    @app.post("/api/payments/{request_id}/reconcile")
    async def reconcile(request_id: str):
        return await app.state.engine.reconcile(request_id)

    @app.get("/api/payments/{request_id}/receipt")
    async def receipt(request_id: str):
        try:
            data = app.state.engine.view(request_id)
        except KeyError:
            raise HTTPException(404, "Not found")
        if not data["receipt"]:
            raise HTTPException(404, "Receipt not available")
        return data["receipt"]

    return app


app = create_app()
