from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Izumi Studio API"
    debug: bool = False
    api_v1_prefix: str = "/v1"
    backend_port: int = 7734
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:2734",
            "http://localhost:2734",
        ]
    )
    data_dir: str = "data"
    uploads_dir: str = "data/uploads"
    sqlite_schema_path: str = "sqlite_schema.sql"
    database_path: str = "data/db.sqlite"
    default_chat_model: str = "deepseek-chat"
    enable_mock_fallback: bool = True
    memory_summary_segment_size: int = 10
    memory_recent_raw_message_count: int = 8
    memory_prompt_summary_limit: int = 3
    memory_prompt_long_term_limit: int = 8

    qwen_api_key: str | None = None
    qwen_api_url: str | None = None
    deepseek_api_key: str | None = None
    deepseek_api_url: str | None = None
    kimi_api_key: str | None = None
    kimi_api_url: str | None = None
    claude_api_key: str | None = None
    claude_api_url: str | None = None

    project_root: Path = Field(default=PROJECT_ROOT)
    backend_root: Path = Field(default=BACKEND_ROOT)

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug_value(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "dev"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod"}:
                return False
        return value

    @field_validator("enable_mock_fallback", mode="before")
    @classmethod
    def normalize_mock_fallback_value(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        return value

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def normalize_cors_allowed_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def resolved_data_dir(self) -> Path:
        return self.project_root / self.data_dir

    @property
    def resolved_uploads_dir(self) -> Path:
        return self.project_root / self.uploads_dir

    @property
    def resolved_schema_path(self) -> Path:
        return self.project_root / self.sqlite_schema_path

    @property
    def resolved_database_path(self) -> Path:
        return self.project_root / self.database_path


@lru_cache
def get_settings() -> Settings:
    return Settings()
