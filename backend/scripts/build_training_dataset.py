from __future__ import annotations

import argparse
import csv
from pathlib import Path

from app.data_sources import (
    _build_team_profiles,
    _competitors_by_home_away,
    _fetch_events,
    _is_completed,
    _parse_date,
    _primary_competition,
    _score,
    _snapshot_from_competitor,
)
from app.models import PredictionRequest, Sport
from app.predictor import _factor_breakdown
from app.trained_model import FEATURE_COLUMNS


def main() -> None:
    parser = argparse.ArgumentParser(description="Build historical win-feature CSV for model training.")
    parser.add_argument("--sports", default="football,basketball,baseball,hockey,soccer", help="Comma-separated sports.")
    parser.add_argument("--days", type=int, default=730, help="Past days to scan.")
    parser.add_argument("--output", default="data/training/win_features.csv", help="Output CSV path.")
    args = parser.parse_args()

    sports = [Sport(value.strip()) for value in args.sports.split(",") if value.strip()]
    rows: list[dict[str, float | int | str]] = []
    for sport in sports:
        rows.extend(_rows_for_sport(sport, args.days))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sport", "game_id", *FEATURE_COLUMNS, "home_won"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output}")


def _rows_for_sport(sport: Sport, days: int) -> list[dict[str, float | int | str]]:
    profiles = _build_team_profiles(sport, days=days)
    rows: list[dict[str, float | int | str]] = []
    for event in _fetch_events(sport, days=days, direction="past"):
        competition = _primary_competition(event)
        if not _is_completed(competition):
            continue
        competitors = _competitors_by_home_away(competition or {})
        if "home" not in competitors or "away" not in competitors:
            continue

        home_score = _score(competitors["home"])
        away_score = _score(competitors["away"])
        if home_score is None or away_score is None or home_score == away_score:
            continue

        event_date = _parse_date(event.get("date"))
        if event_date is None:
            continue

        home = _snapshot_from_competitor(competitors["home"], profiles, event_date)
        away = _snapshot_from_competitor(competitors["away"], profiles, event_date)
        request = PredictionRequest(sport=sport, home_team=home, away_team=away, neutral_site=bool(competition.get("neutralSite", False)))
        factors = _factor_breakdown(request)
        rows.append(
            {
                "sport": sport.value,
                "game_id": str(event.get("id", "")),
                "rating_edge": factors.rating,
                "advanced_rating_edge": factors.advanced_rating,
                "expected_value_edge": factors.expected_value,
                "recent_form_edge": factors.recent_form,
                "injury_edge": factors.injuries,
                "lineup_edge": factors.lineup,
                "rest_edge": factors.rest,
                "venue_edge": factors.venue,
                "travel_edge": factors.travel,
                "market_edge": factors.market,
                "weather_edge": factors.weather,
                "home_won": 1 if home_score > away_score else 0,
            }
        )
    return rows


if __name__ == "__main__":
    main()
