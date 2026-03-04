from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    NATS_URL: str = Field("nats://nats.resto-app.pl:4222", env="NATS_URL")
    NATS_CLIENT_NAME: str = Field("nats-gateway", env="NATS_CLIENT_NAME")

    WS_HOST: str = Field("0.0.0.0", env="WS_HOST")
    WS_PORT: int = Field(8765, env="WS_PORT")

    LOG_DIR: str = Field("logs", env="LOG_DIR")
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")

    HEARTBEAT_EVENT_NAME: str = Field(
        "microcontroller_heartbeat",
        env="HEARTBEAT_EVENT_NAME",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
