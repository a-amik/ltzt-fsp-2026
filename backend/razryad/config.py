"""Настройки сервиса. Всё берётся из окружения, у всего есть значение для разработки."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./razryad.db"
    secret: str = "dev-secret-change-me"
    # Подтверждение почты: "screen" — код показывается в ответе API (стенд, демо),
    # "smtp" — настоящее письмо (после хакатона).
    mail_mode: str = "screen"
    # Провайдер языковой модели: "stub" — правила без модели (в MVP работает только он).
    llm_provider: str = "stub"
    llm_api_key: str = ""
    # Провайдер ФСП ID (OIDC). По умолчанию — мок внутри сервиса; тестовый стенд ФСП подставляется адресом.
    fsp_oidc_issuer: str = "internal"
    grade_cooldown_days: int = 90
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = {"env_prefix": "RZ_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
