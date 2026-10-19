"""Settings, read from the environment once per process. No defaults for secrets."""
import os
from dataclasses import dataclass, field
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    return default if v is None or v == "" else v.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    map_base_url: str = field(default_factory=lambda: os.environ.get("MAP_BASE_URL", "https://h2-app-production.up.railway.app").rstrip("/"))
    anthropic_api_key: str | None = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY") or None)
    tutor_secret: str | None = field(default_factory=lambda: os.environ.get("TUTOR_SECRET") or None)
    model: str = field(default_factory=lambda: os.environ.get("MODEL") or "claude-sonnet-4-5")
    max_tokens: int = field(default_factory=lambda: int(os.environ.get("MAX_TOKENS", "1024")))
    evidence_from_harness: bool = field(default_factory=lambda: _bool("EVIDENCE_FROM_HARNESS", False))
    webhook_budget_s: float = field(default_factory=lambda: float(os.environ.get("WEBHOOK_BUDGET_S", "50")))
    map_timeout_s: float = field(default_factory=lambda: float(os.environ.get("MAP_TIMEOUT_S", "15")))
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get("DATA_DIR", "./data")))


def get_settings() -> Settings:
    return Settings()
