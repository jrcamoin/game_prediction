from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


STATBOMB_RAW_BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"


@dataclass(frozen=True)
class StatBombTeamXg:
    team_name: str
    matches: int
    xg_for: float
    xg_against: float


def statbomb_enabled() -> bool:
    return bool(os.getenv("STATBOMB_OPEN_DATA_DIR") or os.getenv("STATBOMB_ENABLE_REMOTE") == "1")


def statbomb_detail() -> str:
    if os.getenv("STATBOMB_OPEN_DATA_DIR"):
        return "Soccer xG profiles loaded from local StatsBomb open-data JSON."
    if os.getenv("STATBOMB_ENABLE_REMOTE") == "1":
        return "Soccer xG profiles loaded from StatsBomb open-data raw GitHub JSON."
    return "Set STATBOMB_OPEN_DATA_DIR or STATBOMB_ENABLE_REMOTE=1 to enrich soccer predictions with xG."


@lru_cache(maxsize=8)
def team_xg_profiles() -> dict[str, StatBombTeamXg]:
    if not statbomb_enabled():
        return {}

    profiles: dict[str, dict[str, float | set[str] | str]] = {}
    for match in _selected_matches():
        match_id = str(match.get("match_id", ""))
        home_team = _team_name(match.get("home_team"))
        away_team = _team_name(match.get("away_team"))
        if not match_id or not home_team or not away_team:
            continue

        home_xg, away_xg = _match_xg(match_id, home_team, away_team)
        if home_xg is None or away_xg is None:
            continue

        _record_match(profiles, home_team, match_id, home_xg, away_xg)
        _record_match(profiles, away_team, match_id, away_xg, home_xg)

    output: dict[str, StatBombTeamXg] = {}
    for team_name, values in profiles.items():
        match_ids = values["match_ids"]
        if not isinstance(match_ids, set) or not match_ids:
            continue
        matches = len(match_ids)
        output[_normalize(team_name)] = StatBombTeamXg(
            team_name=team_name,
            matches=matches,
            xg_for=round(float(values["xg_for"]) / matches, 3),
            xg_against=round(float(values["xg_against"]) / matches, 3),
        )
    return output


def _selected_matches() -> list[dict]:
    competition_filter = _id_filter("STATBOMB_COMPETITION_IDS")
    season_filter = _id_filter("STATBOMB_SEASON_IDS")
    max_matches = int(os.getenv("STATBOMB_MAX_MATCHES", "250"))
    matches: list[dict] = []

    for competition in _read_json("competitions.json"):
        competition_id = str(competition.get("competition_id", ""))
        season_id = str(competition.get("season_id", ""))
        if competition_filter and competition_id not in competition_filter:
            continue
        if season_filter and season_id not in season_filter:
            continue
        if competition.get("competition_youth"):
            continue

        season_matches = _read_json(f"matches/{competition_id}/{season_id}.json")
        if isinstance(season_matches, list):
            matches.extend(season_matches)
        if len(matches) >= max_matches:
            return matches[:max_matches]
    return matches[:max_matches]


def _match_xg(match_id: str, home_team: str, away_team: str) -> tuple[float | None, float | None]:
    home_xg = 0.0
    away_xg = 0.0
    saw_shot = False
    events = _read_json(f"events/{match_id}.json")
    if not isinstance(events, list):
        return None, None

    for event in events:
        if event.get("type", {}).get("name") != "Shot":
            continue
        team = _team_name(event.get("team"))
        xg = event.get("shot", {}).get("statsbomb_xg")
        if team is None or xg is None:
            continue
        saw_shot = True
        if _normalize(team) == _normalize(home_team):
            home_xg += float(xg)
        elif _normalize(team) == _normalize(away_team):
            away_xg += float(xg)

    if not saw_shot:
        return None, None
    return home_xg, away_xg


def _record_match(profiles: dict[str, dict[str, float | set[str] | str]], team: str, match_id: str, xg_for: float, xg_against: float) -> None:
    values = profiles.setdefault(team, {"team_name": team, "match_ids": set(), "xg_for": 0.0, "xg_against": 0.0})
    match_ids = values["match_ids"]
    if not isinstance(match_ids, set) or match_id in match_ids:
        return
    match_ids.add(match_id)
    values["xg_for"] = float(values["xg_for"]) + xg_for
    values["xg_against"] = float(values["xg_against"]) + xg_against


def _read_json(relative_path: str) -> list | dict:
    root = os.getenv("STATBOMB_OPEN_DATA_DIR")
    if root:
        path = Path(root) / relative_path
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

    if os.getenv("STATBOMB_ENABLE_REMOTE") != "1":
        return []

    url = f"{STATBOMB_RAW_BASE_URL}/{relative_path}"
    request = Request(url, headers={"User-Agent": "game-predictor/0.3"})
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return []


def _id_filter(env_name: str) -> set[str]:
    return {part.strip() for part in os.getenv(env_name, "").split(",") if part.strip()}


def _team_name(value: dict | None) -> str | None:
    if not value:
        return None
    name = value.get("name")
    return str(name) if name else None


def _normalize(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())
