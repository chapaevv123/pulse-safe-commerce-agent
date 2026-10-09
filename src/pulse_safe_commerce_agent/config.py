from __future__ import annotations

import os
from dataclasses import dataclass

SANDBOX_URL = "https://api-m.sandbox.paypal.com"


@dataclass(frozen=True)
class Settings:
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_base_url: str = SANDBOX_URL
    app_base_url: str = "http://localhost:8000"
    database_path: str = "./safe_commerce.db"
    ai_provider: str = "fixture"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1-mini"
    session_secret: str = "development-only-change-me"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(**{f: os.getenv(k, d) for f, k, d in (
            ("paypal_client_id", "PAYPAL_CLIENT_ID", ""),
            ("paypal_client_secret", "PAYPAL_CLIENT_SECRET", ""),
            ("paypal_base_url", "PAYPAL_BASE_URL", SANDBOX_URL),
            ("app_base_url", "APP_BASE_URL", "http://localhost:8000"),
            ("database_path", "DATABASE_PATH", "./safe_commerce.db"),
            ("ai_provider", "AI_PROVIDER", "fixture"),
            ("openai_api_key", "OPENAI_API_KEY", ""),
            ("openai_base_url", "OPENAI_BASE_URL", "https://api.openai.com/v1"),
            ("openai_model", "OPENAI_MODEL", "gpt-4.1-mini"),
            ("session_secret", "SESSION_SECRET", "development-only-change-me"),
        )})

    def validate(self) -> None:
        if self.paypal_base_url.rstrip("/") != SANDBOX_URL:
            raise ValueError("Only the PayPal Sandbox base URL is allowed")

    @property
    def paypal_ready(self) -> bool:
        return bool(self.paypal_client_id and self.paypal_client_secret)
