from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "sago-reengage-agent"
    log_level: str = "INFO"
    database_url: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/sago_reengage"
    )
    db_connect_timeout: int = 5
    db_check_on_startup: bool = True
    drive_folder_id: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_prefix="",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
