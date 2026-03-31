from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(validation_alias="DATABASE_URL")
    redis_url: str = Field(validation_alias="REDIS_URL")
    kafka_bootstrap_servers: str = Field(validation_alias="KAFKA_BOOTSTRAP_SERVERS")
    jwt_secret: str = Field(validation_alias="JWT_SECRET")
    google_client_id: str = Field(default="", validation_alias="GOOGLE_CLIENT_ID")
    metrics_api_key: str = Field(default="", validation_alias="METRICS_API_KEY")
    razorpay_key_id: str = Field(default="", validation_alias="RAZORPAY_KEY_ID")
    razorpay_key_secret: str = Field(default="", validation_alias="RAZORPAY_KEY_SECRET")
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:4000",
            "http://localhost:3001", # Add the fallback port your Next.js app is using
            "http://127.0.0.1:4000",
            "http://127.0.0.1:3001",
        ],
        validation_alias="CORS_ORIGINS",
    )
    cors_allow_methods: list[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        validation_alias="CORS_ALLOW_METHODS",
    )
    cors_allow_headers: list[str] = Field(
        default_factory=lambda: [
            "Content-Type",
            "Authorization",
            "Accept",
            "Origin",
            "X-Request-ID",
            "Idempotency-Key",
        ],
        validation_alias="CORS_ALLOW_HEADERS",
    )

    @field_validator("cors_origins", "cors_allow_methods", "cors_allow_headers", mode="before")
    @classmethod
    def _parse_csv_list(cls, value: Any) -> Any:
        import json
        if isinstance(value, str):
            clean_value = value.strip()
            # Handle JSON array strings like '["http://localhost:3000"]'
            if clean_value.startswith("[") and clean_value.endswith("]"):
                try:
                    return json.loads(clean_value)
                except json.JSONDecodeError:
                    pass
            # Fallback to CSV parsing
            return [item.strip() for item in clean_value.split(",") if item.strip()]
        return value


settings = Settings()
