from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.models import DataSourceStatus, GameSnapshot, Sport, TeamSnapshot


def read_provider_json(path_value: str | None) -> list[dict[str, Any]]:
    if not path_value:
        return []
    path = Path(path_value)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("events"), list):
        return [item for item in payload["events"] if isinstance(item, dict)]
    return []


def fetch_json_url(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "game-predictor/0.4"})
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def snapshot_from_record(record: dict[str, Any], prefix: str, source: str) -> TeamSnapshot:
    return TeamSnapshot(
        id=_string_or_none(record.get(f"{prefix}_id")),
        name=str(record.get(f"{prefix}_name") or record.get(prefix) or "Unknown"),
        abbreviation=_string_or_none(record.get(f"{prefix}_abbreviation")),
        rating=float(record.get(f"{prefix}_rating", 1500)),
        recent_wins=int(record.get(f"{prefix}_recent_wins", 3)),
        recent_losses=int(record.get(f"{prefix}_recent_losses", 2)),
        injuries=int(record.get(f"{prefix}_injuries", 0)),
        questionable_players=int(record.get(f"{prefix}_questionable_players", 0)),
        starters_confirmed=int(record.get(f"{prefix}_starters_confirmed", 1)),
        projected_starters=int(record.get(f"{prefix}_projected_starters", 1)),
        rest_days=int(record.get(f"{prefix}_rest_days", 5)),
        moneyline=_int_or_none(record.get(f"{prefix}_moneyline")),
        expected_value_for=_float_or_none(record.get(f"{prefix}_expected_value_for")),
        expected_value_against=_float_or_none(record.get(f"{prefix}_expected_value_against")),
        source=source,
    )


def game_from_record(record: dict[str, Any], sport: Sport, source_name: str, source_detail: str) -> GameSnapshot:
    date = _parse_date(str(record.get("date", ""))).isoformat()
    home = snapshot_from_record(record, "home", source_name)
    away = snapshot_from_record(record, "away", source_name)
    return GameSnapshot(
        id=str(record.get("id") or f"{sport.value}:{away.name}:{home.name}:{date}"),
        sport=sport,
        date=date,
        name=str(record.get("name") or f"{away.name} vs {home.name}"),
        home_team=home,
        away_team=away,
        neutral_site=bool(record.get("neutral_site", True)),
        home_travel_miles=int(record.get("home_travel_miles", 0)),
        away_travel_miles=int(record.get("away_travel_miles", 0)),
        venue_name=_string_or_none(record.get("venue_name")),
        venue_city=_string_or_none(record.get("venue_city")),
        venue_state=_string_or_none(record.get("venue_state")),
        sources=[
            DataSourceStatus(name=source_name, enabled=True, detail=source_detail),
        ],
    )


def _parse_date(value: str) -> datetime:
    if value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(UTC)


def _string_or_none(value: Any) -> str | None:
    return None if value is None else str(value)


def _int_or_none(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
