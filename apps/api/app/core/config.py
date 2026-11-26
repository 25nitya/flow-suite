
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Flow Suite"
    environment: str = "development"
    api_prefix: str = "/api"
    cors_origins: str = (
        "http://localhost:5173,"
        "http://localhost:3000,"
        "http://localhost:3001,"
        "http://localhost"
    )

    database_url: str = (
        "postgresql+asyncpg://flowsuite:flowsuite@postgres:5432/flowsuite"
    )
    redis_url: str = "redis://redis:6379/0"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14

    # Razorpay configuration
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    frontend_url: str = "http://localhost:3001"

    # Temporary: retained until the Stripe router is replaced.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro: str = ""
    stripe_price_business: str = ""
    billing_stub_mode: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
