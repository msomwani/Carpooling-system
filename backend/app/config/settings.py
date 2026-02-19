from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    database_url: str = Field(validation_alias="DATABASE_URL")
    jwt_secret: str = Field(validation_alias="JWT_SECRET")
    redis_url: str = Field(validation_alias="REDIS_URL")
    kafka_bootstrap_servers: str = Field(validation_alias="KAFKA_BOOTSTRAP_SERVERS")


settings = Settings()
