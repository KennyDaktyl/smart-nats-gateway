# core/config.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    NATS_URL: str = Field("nats://nats.resto-app.pl:4222", env="NATS_URL")
    LOG_DIR: str = Field("logs", env="LOG_DIR")
    BACKEND_API_URL: str = Field("http://smart-api.resto-app.pl", env="BACKEND_API_URL")
    RASPBERRY_EVENTS_SUBJECT_TEMPLATE: str = Field(
        "device_communication.raspberry.{uuid}.events",
        env="RASPBERRY_EVENTS_SUBJECT_TEMPLATE",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
