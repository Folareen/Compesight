from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Compesight API"
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:3000"]

    database_url: str = "postgresql+asyncpg://compesight:compesight@localhost:5432/compesight"

    redis_url: str = "redis://localhost:6379/0"

    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""
    clerk_issuer: str = ""

    crawler_user_agent: str = "CompesightBot/1.0 (+https://compesight.example/bot)"
    crawl_timeout_ms: int = 30_000
    crawl_min_host_interval_seconds: float = 2.0
    crawl_backoff_base_seconds: float = 5.0
    crawl_backoff_cap_seconds: float = 600.0
    crawl_backoff_jitter_seconds: float = 3.0
    scheduler_enqueue_jitter_seconds: int = 60
    source_lock_ttl_seconds: int = 300
    robots_cache_ttl_seconds: int = 3600


settings = Settings()
