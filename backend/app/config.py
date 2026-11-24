from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"

    # Database
    database_url: str

    # Frontend
    cors_origins: str = "http://localhost:3000"

    # SQLAlchemy
    sql_echo: bool = False

    # LLM provider
    llm_base_url: str = "http://127.0.0.1:11434"
    llm_api_key: str = "ollama"
    llm_model: str = "qwen3.5:2b"
    llm_timeout_seconds: float = 120.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()