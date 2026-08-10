from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

# 项目根目录 (backend/ 的父目录)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 媒体文件存储目录 (静态服务挂载到 /media)
MEDIA_DIR = BASE_DIR / "data" / "media"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用
    app_name: str = "徒步助手"
    app_version: str = "0.1.0"
    debug: bool = True
    secret_key: str = "change-me-in-production-use-a-real-secret-key"

    # 数据库 (默认 SQLite 开发，生产用 PostgreSQL)
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'hiking.db'}"

    # Redis (Celery 任务队列，暂未使用)
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 天

    # LLM API
    # 支持 Anthropic Claude 和 DeepSeek（OpenAI 兼容）
    # 默认使用 DeepSeek
    llm_provider: str = Field(default="deepseek", alias="LLM_PROVIDER")  # deepseek | anthropic

    # Anthropic
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-4-20250514", alias="HIKING_ANTHROPIC_MODEL")
    anthropic_base_url: str = Field(default="https://api.anthropic.com", alias="HIKING_ANTHROPIC_BASE_URL")

    # DeepSeek (OpenAI 兼容)
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    deepseek_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_MODEL")
    deepseek_base_url: str = Field(default="https://api.deepseek.com", alias="DEEPSEEK_BASE_URL")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # 搜索 API
    tavily_api_key: str = ""

    # 天气 API
    openweather_api_key: str = ""

    # 文件存储
    upload_dir: str = "../data"
    max_upload_size_mb: int = 100


@lru_cache()
def get_settings() -> Settings:
    return Settings()
