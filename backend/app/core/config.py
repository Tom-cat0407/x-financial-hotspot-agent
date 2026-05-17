from __future__ import annotations

import os
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT_DIR / "data"
OUTPUTS_DIR = ROOT_DIR / "outputs"
CARDS_DIR = OUTPUTS_DIR / "cards"
REPORTS_DIR = OUTPUTS_DIR / "reports"
STATE_FILE = OUTPUTS_DIR / "state.json"


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        value = value.strip()
        if " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


if not any("pytest" in arg.lower() for arg in sys.argv):
    _load_env_file(ROOT_DIR / ".env")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw!r}") from exc


def _env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


class Settings(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    app_name: str = "X Financial Hotspot Agent"
    x_mode: str = Field(default_factory=lambda: os.getenv("X_MODE", "mock"))
    enable_real_publish: bool = Field(default_factory=lambda: _env_bool("ENABLE_REAL_PUBLISH", False))
    review_required: bool = Field(default_factory=lambda: _env_bool("REVIEW_REQUIRED", True))
    max_posts_per_hour: int = Field(default_factory=lambda: _env_int("MAX_POSTS_PER_HOUR", 6))
    publish_max_retries: int = Field(default_factory=lambda: _env_int("PUBLISH_MAX_RETRIES", 2))
    public_base_url: str = Field(default_factory=lambda: os.getenv("PUBLIC_BASE_URL", "http://localhost:8000"))
    use_database: bool = Field(default_factory=lambda: _env_bool("USE_DATABASE", False))
    database_url: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://agent:agent_password@localhost:5432/x_hotspot_agent",
        )
    )
    db_fallback_to_json: bool = Field(default_factory=lambda: _env_bool("DB_FALLBACK_TO_JSON", True))
    llm_provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai_compatible"))
    llm_api_key: str = Field(default_factory=lambda: _env_first("LLM_API_KEY", "DEEPSEEK_API_KEY"))
    llm_base_url: str = Field(default_factory=lambda: os.getenv("LLM_BASE_URL", "https://api.deepseek.com"))
    llm_model: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", "deepseek-chat"))
    llm_timeout_seconds: int = Field(default_factory=lambda: _env_int("LLM_TIMEOUT_SECONDS", 30))
    llm_max_retries: int = Field(default_factory=lambda: _env_int("LLM_MAX_RETRIES", 2))
    llm_retry_base_seconds: float = Field(default_factory=lambda: _env_float("LLM_RETRY_BASE_SECONDS", 1.5))
    llm_reasoning_effort: str = Field(default_factory=lambda: os.getenv("LLM_REASONING_EFFORT", ""))
    llm_thinking_enabled: bool = Field(default_factory=lambda: _env_bool("LLM_THINKING_ENABLED", False))
    enable_llm_ner: bool = Field(default_factory=lambda: _env_bool("ENABLE_LLM_NER", False))
    llm_ner_max_posts_per_run: int = Field(default_factory=lambda: _env_int("LLM_NER_MAX_POSTS_PER_RUN", 8))
    enable_scheduler: bool = Field(default_factory=lambda: _env_bool("ENABLE_SCHEDULER", False))
    collection_interval_minutes: int = Field(default_factory=lambda: _env_int("COLLECTION_INTERVAL_MINUTES", 5))
    enable_ab_testing: bool = Field(default_factory=lambda: _env_bool("ENABLE_AB_TESTING", True))
    enable_external_fact_sources: bool = Field(default_factory=lambda: _env_bool("ENABLE_EXTERNAL_FACT_SOURCES", False))
    telegram_enabled: bool = Field(default_factory=lambda: _env_bool("TELEGRAM_ENABLED", False))
    telegram_bot_token: str = Field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = Field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))
    telegram_timeout_seconds: int = Field(default_factory=lambda: _env_int("TELEGRAM_TIMEOUT_SECONDS", 10))
    threads_enabled: bool = Field(default_factory=lambda: _env_bool("THREADS_ENABLED", False))
    threads_mode: str = Field(default_factory=lambda: os.getenv("THREADS_MODE", "mock"))
    alert_webhook_url: str = Field(default_factory=lambda: os.getenv("ALERT_WEBHOOK_URL", ""))
    alert_timeout_seconds: int = Field(default_factory=lambda: _env_int("ALERT_TIMEOUT_SECONDS", 5))

    @field_validator("max_posts_per_hour", "llm_timeout_seconds", "collection_interval_minutes", "telegram_timeout_seconds", "alert_timeout_seconds")
    @classmethod
    def _positive_int(cls, value: int) -> int:
        if value < 1:
            raise ValueError("must be greater than or equal to 1")
        return value

    @field_validator("llm_max_retries", "llm_ner_max_posts_per_run", "publish_max_retries")
    @classmethod
    def _non_negative_int(cls, value: int) -> int:
        if value < 0:
            raise ValueError("must be greater than or equal to 0")
        return value

    @field_validator("llm_retry_base_seconds")
    @classmethod
    def _non_negative_float(cls, value: float) -> float:
        if value < 0:
            raise ValueError("must be greater than or equal to 0")
        return value

    @field_validator("public_base_url", "llm_base_url")
    @classmethod
    def _strip_url(cls, value: str) -> str:
        return value.rstrip("/")


settings = Settings()
