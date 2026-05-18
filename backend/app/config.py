"""Application settings.

`AIM_ROOT` is the single, mandatory runtime root for the platform.
On the operator's workstation it is the Windows path baked into the
spec; in containers it is the bind-mount target (/data/aim-root); in
dev on Linux/macOS it is whatever the developer points it at via .env.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    aim_root: Path = Field(default=Path(r"C:\Users\ASUS\Desktop\AI Manager"))

    # Path to the standalone "AI Metodist Agent" Python package that powers the
    # `app.agents.metodist` sub-agent. The wrapper imports `metodist_agent.agent`
    # (operator runs `pip install -e <this path>` into the platform venv) and
    # reads this folder's `.env` for `ANTHROPIC_API_KEY`. See agents/metodist.py.
    metodist_standalone_path: Path = Field(
        default=Path(r"C:\Users\ASUS\Desktop\AI Manager\KB\AI Metodist Agent")
    )

    database_url: str = "postgresql+asyncpg://ai_manager:change-me@postgres:5432/ai_manager"
    redis_url: str = "redis://redis:6379/0"

    ollama_host: str = "http://ollama:11434"
    ollama_model_router: str = "qwen2.5:7b-instruct"
    ollama_model_synth: str = "llama3.1:8b"
    ollama_model_embed: str = "bge-m3"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    jwt_secret: str = "dev-only-not-secret"
    jwt_alg: str = "HS256"
    jwt_ttl_min: int = 480

    crawl_cron: str = "0 3 * * *"
    crawl_allowed_hosts: str = "lex.uz,cbu.uz,ipakyulibank.uz"

    tesseract_langs: str = "rus+uzb+uzb_cyrl+eng"

    # Derived KB sub-paths -----------------------------------------------------
    @property
    def kb(self) -> Path:
        return self.aim_root / "KB"

    @property
    def kb_raw(self) -> Path:
        return self.kb / "Raw"

    @property
    def kb_processed(self) -> Path:
        return self.kb / "Processed"

    @property
    def kb_regulator(self) -> Path:
        return self.kb / "Regulator"

    @property
    def kb_lotus(self) -> Path:
        return self.kb / "Lotus"

    @property
    def kb_temp(self) -> Path:
        return self.kb / "Temp"

    @property
    def archive(self) -> Path:
        return self.aim_root / "Archive"

    @property
    def logs(self) -> Path:
        return self.aim_root / "Logs"

    @property
    def cache(self) -> Path:
        return self.aim_root / "Cache"

    @property
    def allowed_hosts(self) -> tuple[str, ...]:
        return tuple(h.strip() for h in self.crawl_allowed_hosts.split(",") if h.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
