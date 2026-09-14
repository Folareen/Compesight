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


settings = Settings()
