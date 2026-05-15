"""Carga de configuracion desde variables de entorno."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Cargar .env del directorio raiz del proyecto
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _get_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_list(name: str, sep: str = ",") -> List[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(sep) if x.strip()]


@dataclass
class ScraperConfig:
    interval_minutes: int = 60
    delay_min: float = 2.0
    delay_max: float = 5.0
    max_pages_per_search: int = 5
    user_agent_rotate: bool = True
    proxies: List[str] = field(default_factory=list)
    search_targets_file: str = "config/search_targets.json"


@dataclass
class SupabaseConfig:
    url: str = ""
    key: str = ""

    @property
    def enabled(self) -> bool:
        return bool(self.url and self.key)


@dataclass
class EmailConfig:
    host: str = ""
    port: int = 587
    user: str = ""
    password: str = ""
    from_addr: str = ""
    to_addr: str = ""

    @property
    def enabled(self) -> bool:
        return bool(self.host and self.user and self.from_addr and self.to_addr)


@dataclass
class TelegramConfig:
    bot_token: str = ""
    chat_id: str = ""

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token and self.chat_id)


@dataclass
class AlertConfig:
    min_score_high: int = 80
    min_score_price_drop: int = 60
    price_drop_pct: float = 5.0


@dataclass
class LogConfig:
    level: str = "INFO"
    file: str = "logs/scraper.jsonl"


@dataclass
class AppConfig:
    scraper: ScraperConfig
    supabase: SupabaseConfig
    email: EmailConfig
    telegram: TelegramConfig
    alerts: AlertConfig
    logs: LogConfig

    @classmethod
    def load(cls) -> "AppConfig":
        return cls(
            scraper=ScraperConfig(
                interval_minutes=_get_int("SCRAPER_INTERVAL_MINUTES", 60),
                delay_min=_get_float("SCRAPER_DELAY_MIN", 2.0),
                delay_max=_get_float("SCRAPER_DELAY_MAX", 5.0),
                max_pages_per_search=_get_int("SCRAPER_MAX_PAGES_PER_SEARCH", 5),
                user_agent_rotate=_get_bool("SCRAPER_USER_AGENT_ROTATE", True),
                proxies=_get_list("SCRAPER_PROXIES"),
                search_targets_file=os.getenv(
                    "SEARCH_TARGETS_FILE", "config/search_targets.json"
                ),
            ),
            supabase=SupabaseConfig(
                url=os.getenv("SUPABASE_URL", ""),
                key=os.getenv("SUPABASE_KEY", ""),
            ),
            email=EmailConfig(
                host=os.getenv("SMTP_HOST", ""),
                port=_get_int("SMTP_PORT", 587),
                user=os.getenv("SMTP_USER", ""),
                password=os.getenv("SMTP_PASS", ""),
                from_addr=os.getenv("ALERT_EMAIL_FROM", ""),
                to_addr=os.getenv("ALERT_EMAIL_TO", ""),
            ),
            telegram=TelegramConfig(
                bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
                chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            ),
            alerts=AlertConfig(
                min_score_high=_get_int("ALERT_MIN_SCORE_HIGH", 80),
                min_score_price_drop=_get_int("ALERT_MIN_SCORE_PRICE_DROP", 60),
                price_drop_pct=_get_float("ALERT_PRICE_DROP_PCT", 5.0),
            ),
            logs=LogConfig(
                level=os.getenv("LOG_LEVEL", "INFO"),
                file=os.getenv("LOG_FILE", "logs/scraper.jsonl"),
            ),
        )

    def load_search_targets(self) -> List[dict]:
        path = Path(self.scraper.search_targets_file)
        if not path.is_absolute():
            path = ROOT_DIR / path
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("targets", [])


# Instancia singleton
config = AppConfig.load()
