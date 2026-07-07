from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path


APP_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "WaterBuddy"
STATE_PATH = APP_DIR / "state.json"
DRINK_AMOUNT_OPTIONS = (100, 150, 250, 300)


@dataclass
class DrinkEntry:
    amount_ml: int
    created_at: str


@dataclass
class Settings:
    daily_goal_ml: int = 1600
    cup_size_ml: int = 250
    remind_every_minutes: int = 45
    quiet_start: str = "22:30"
    quiet_end: str = "08:30"
    paused_until: str | None = None
    start_on_boot: bool = False


@dataclass
class AppState:
    settings: Settings = field(default_factory=Settings)
    entries: list[DrinkEntry] = field(default_factory=list)


def today_key() -> str:
    return date.today().isoformat()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_state(day: str | None = None) -> AppState:
    target_day = day or today_key()
    if not STATE_PATH.exists():
        return AppState()

    try:
        raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AppState()

    settings_raw = raw.get("settings", {})
    entries_raw = raw.get("entries", {}).get(target_day, [])
    settings_defaults = asdict(Settings())
    safe_settings = {key: settings_raw.get(key, value) for key, value in settings_defaults.items()}
    settings = Settings(**safe_settings)
    if settings.cup_size_ml not in DRINK_AMOUNT_OPTIONS:
        settings.cup_size_ml = min(DRINK_AMOUNT_OPTIONS, key=lambda option: abs(option - settings.cup_size_ml))
    entries = [
        DrinkEntry(amount_ml=int(item.get("amount_ml", settings.cup_size_ml)), created_at=str(item.get("created_at", now_iso())))
        for item in entries_raw
    ]
    return AppState(settings=settings, entries=entries)


def save_state(state: AppState, day: str | None = None) -> None:
    target_day = day or today_key()
    APP_DIR.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if STATE_PATH.exists():
        try:
            existing = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}

    entries_by_day = existing.get("entries", {})
    entries_by_day[target_day] = [asdict(entry) for entry in state.entries]
    payload = {
        "settings": asdict(state.settings),
        "entries": entries_by_day,
    }
    STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def total_today_ml(state: AppState) -> int:
    return sum(entry.amount_ml for entry in state.entries)
