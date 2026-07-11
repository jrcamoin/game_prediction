from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.models import (
    CommunityDashboard,
    Contest,
    ContestCreate,
    ContestEntry,
    ContestEntryCreate,
    Favorite,
    FavoriteCreate,
    Follow,
    FollowCreate,
    GameResult,
    GameComment,
    GameCommentCreate,
    GameSnapshot,
    LeaderboardEntry,
    ModelPerformanceReport,
    NotificationPreferences,
    Plan,
    PredictionResponse,
    PredictionSummary,
    PublicProfile,
    SavedPrediction,
    Sport,
    UserProfile,
    UserProfileCreate,
    WeeklyChallenge,
)


DATABASE_PATH = Path(os.getenv("GAME_PREDICTOR_DB", "data/game_predictor.sqlite3"))


def init_db() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                game_id TEXT NOT NULL,
                sport TEXT NOT NULL,
                game_date TEXT NOT NULL,
                game_name TEXT NOT NULL,
                predicted_winner TEXT NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                home_win_probability REAL NOT NULL,
                away_win_probability REAL NOT NULL,
                confidence TEXT NOT NULL,
                score REAL NOT NULL,
                response_json TEXT NOT NULL,
                game_json TEXT NOT NULL,
                actual_winner TEXT,
                correct INTEGER,
                resolved_at TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_predictions_game
            ON predictions (sport, game_id)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                display_name TEXT NOT NULL,
                email TEXT,
                created_at TEXT NOT NULL,
                plan TEXT NOT NULL DEFAULT 'free',
                daily_email INTEGER NOT NULL DEFAULT 0,
                push_alerts INTEGER NOT NULL DEFAULT 0,
                close_game_alerts INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        _ensure_column(connection, "users", "plan", "TEXT NOT NULL DEFAULT 'free'")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sport TEXT NOT NULL,
                team_id TEXT,
                team_name TEXT,
                league_name TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS follows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                follower_id INTEGER NOT NULL,
                following_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(follower_id, following_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sport TEXT NOT NULL,
                game_id TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS contests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                sport TEXT NOT NULL,
                starts_at TEXT,
                ends_at TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS contest_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contest_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                prediction_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(contest_id, user_id, prediction_id)
            )
            """
        )


def save_live_prediction(game: GameSnapshot, prediction: PredictionResponse) -> SavedPrediction:
    init_db()
    created_at = _now()
    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO predictions (
                created_at, game_id, sport, game_date, game_name, predicted_winner,
                home_team, away_team, home_win_probability, away_win_probability,
                confidence, score, response_json, game_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                game.id,
                game.sport.value,
                game.date,
                game.name,
                prediction.predicted_winner,
                game.home_team.name,
                game.away_team.name,
                prediction.home_win_probability,
                prediction.away_win_probability,
                prediction.confidence,
                prediction.score,
                json.dumps(prediction.model_dump()),
                json.dumps(game.model_dump()),
            ),
        )
        row = connection.execute("SELECT * FROM predictions WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _row_to_prediction(row)


def list_predictions(limit: int = 25, query: str | None = None, sport: Sport | None = None) -> list[SavedPrediction]:
    init_db()
    bounded_limit = min(max(limit, 1), 100)
    filters: list[str] = []
    values: list[Any] = []
    if query:
        filters.append("(game_name LIKE ? OR predicted_winner LIKE ? OR home_team LIKE ? OR away_team LIKE ?)")
        search = f"%{query}%"
        values.extend([search, search, search, search])
    if sport:
        filters.append("sport = ?")
        values.append(sport.value)

    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    with _connect() as connection:
        rows = connection.execute(
            f"SELECT * FROM predictions {where} ORDER BY created_at DESC, id DESC LIMIT ?",
            (*values, bounded_limit),
        ).fetchall()
    return [_row_to_prediction(row) for row in rows]


def prediction_summary() -> PredictionSummary:
    init_db()
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN correct IS NOT NULL THEN 1 ELSE 0 END) AS resolved,
                SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END) AS correct
            FROM predictions
            """
        ).fetchone()

    total = int(row["total"] or 0)
    resolved = int(row["resolved"] or 0)
    correct = int(row["correct"] or 0)
    return PredictionSummary(
        total=total,
        resolved=resolved,
        correct=correct,
        accuracy=round(correct / resolved, 4) if resolved else None,
        pending=total - resolved,
    )


def unresolved_predictions() -> list[SavedPrediction]:
    init_db()
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM predictions WHERE correct IS NULL ORDER BY game_date ASC, id ASC LIMIT 100"
        ).fetchall()
    return [_row_to_prediction(row) for row in rows]


def mark_prediction_resolved(prediction_id: int, result: GameResult) -> SavedPrediction | None:
    if not result.completed or result.winner is None:
        return None

    resolved_at = _now()
    with _connect() as connection:
        row = connection.execute("SELECT * FROM predictions WHERE id = ?", (prediction_id,)).fetchone()
        if row is None:
            return None
        correct = row["predicted_winner"].casefold() == result.winner.casefold()
        connection.execute(
            """
            UPDATE predictions
            SET actual_winner = ?, correct = ?, resolved_at = ?
            WHERE id = ?
            """,
            (result.winner, 1 if correct else 0, resolved_at, prediction_id),
        )
        updated = connection.execute("SELECT * FROM predictions WHERE id = ?", (prediction_id,)).fetchone()
    return _row_to_prediction(updated)


def create_user_profile(profile: UserProfileCreate) -> UserProfile:
    init_db()
    created_at = _now()
    with _connect() as connection:
        cursor = connection.execute(
            "INSERT INTO users (display_name, email, created_at) VALUES (?, ?, ?)",
            (profile.display_name, profile.email, created_at),
        )
        row = connection.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _row_to_user(row)


def list_user_profiles() -> list[UserProfile]:
    init_db()
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM users ORDER BY created_at DESC, id DESC").fetchall()
    return [_row_to_user(row) for row in rows]


def get_user_profile(user_id: int) -> UserProfile | None:
    init_db()
    with _connect() as connection:
        row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _row_to_user(row) if row else None


def update_user_plan(user_id: int, plan: Plan) -> UserProfile | None:
    init_db()
    with _connect() as connection:
        connection.execute("UPDATE users SET plan = ? WHERE id = ?", (plan.value, user_id))
        row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _row_to_user(row) if row else None


def update_notification_preferences(user_id: int, preferences: NotificationPreferences) -> UserProfile | None:
    init_db()
    with _connect() as connection:
        connection.execute(
            """
            UPDATE users
            SET daily_email = ?, push_alerts = ?, close_game_alerts = ?
            WHERE id = ?
            """,
            (
                1 if preferences.daily_email else 0,
                1 if preferences.push_alerts else 0,
                1 if preferences.close_game_alerts else 0,
                user_id,
            ),
        )
        row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _row_to_user(row) if row else None


def add_favorite(user_id: int, favorite: FavoriteCreate) -> Favorite:
    init_db()
    created_at = _now()
    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO favorites (user_id, sport, team_id, team_name, league_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                favorite.sport.value,
                favorite.team_id,
                favorite.team_name,
                favorite.league_name,
                created_at,
            ),
        )
        row = connection.execute("SELECT * FROM favorites WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _row_to_favorite(row)


def list_favorites(user_id: int) -> list[Favorite]:
    init_db()
    with _connect() as connection:
        rows = connection.execute(
            "SELECT * FROM favorites WHERE user_id = ? ORDER BY created_at DESC, id DESC",
            (user_id,),
        ).fetchall()
    return [_row_to_favorite(row) for row in rows]


def delete_favorite(user_id: int, favorite_id: int) -> None:
    init_db()
    with _connect() as connection:
        connection.execute("DELETE FROM favorites WHERE user_id = ? AND id = ?", (user_id, favorite_id))


def list_public_profiles() -> list[PublicProfile]:
    init_db()
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM users ORDER BY created_at DESC, id DESC").fetchall()
    return [_public_profile(row["id"]) for row in rows]


def get_public_profile(user_id: int) -> PublicProfile | None:
    init_db()
    if get_user_profile(user_id) is None:
        return None
    return _public_profile(user_id)


def follow_user(follow: FollowCreate) -> Follow:
    init_db()
    if follow.follower_id == follow.following_id:
        raise ValueError("users cannot follow themselves")
    created_at = _now()
    with _connect() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO follows (follower_id, following_id, created_at)
            VALUES (?, ?, ?)
            """,
            (follow.follower_id, follow.following_id, created_at),
        )
        row = connection.execute(
            "SELECT * FROM follows WHERE follower_id = ? AND following_id = ?",
            (follow.follower_id, follow.following_id),
        ).fetchone()
    return _row_to_follow(row)


def unfollow_user(follower_id: int, following_id: int) -> None:
    init_db()
    with _connect() as connection:
        connection.execute("DELETE FROM follows WHERE follower_id = ? AND following_id = ?", (follower_id, following_id))


def list_following(user_id: int) -> list[PublicProfile]:
    init_db()
    with _connect() as connection:
        rows = connection.execute("SELECT following_id FROM follows WHERE follower_id = ?", (user_id,)).fetchall()
    return [_public_profile(row["following_id"]) for row in rows]


def add_game_comment(comment: GameCommentCreate) -> GameComment:
    init_db()
    created_at = _now()
    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO comments (user_id, sport, game_id, body, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (comment.user_id, comment.sport.value, comment.game_id, comment.body, created_at),
        )
        row = connection.execute(
            """
            SELECT comments.*, users.display_name
            FROM comments
            JOIN users ON users.id = comments.user_id
            WHERE comments.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return _row_to_comment(row)


def list_game_comments(sport: Sport, game_id: str) -> list[GameComment]:
    init_db()
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT comments.*, users.display_name
            FROM comments
            JOIN users ON users.id = comments.user_id
            WHERE comments.sport = ? AND comments.game_id = ?
            ORDER BY comments.created_at DESC, comments.id DESC
            LIMIT 100
            """,
            (sport.value, game_id),
        ).fetchall()
    return [_row_to_comment(row) for row in rows]


def create_contest(contest: ContestCreate) -> Contest:
    init_db()
    created_at = _now()
    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO contests (name, sport, starts_at, ends_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (contest.name.strip(), contest.sport.value, contest.starts_at, contest.ends_at, created_at),
        )
        row = connection.execute("SELECT * FROM contests WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _row_to_contest(row)


def list_contests() -> list[Contest]:
    init_db()
    _ensure_default_contest()
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM contests ORDER BY created_at DESC, id DESC LIMIT 20").fetchall()
    return [_row_to_contest(row) for row in rows]


def add_contest_entry(contest_id: int, entry: ContestEntryCreate) -> ContestEntry:
    init_db()
    created_at = _now()
    with _connect() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO contest_entries (contest_id, user_id, prediction_id, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (contest_id, entry.user_id, entry.prediction_id, created_at),
        )
        row = connection.execute(
            """
            SELECT contest_entries.*, users.display_name, predictions.predicted_winner, predictions.correct
            FROM contest_entries
            JOIN users ON users.id = contest_entries.user_id
            JOIN predictions ON predictions.id = contest_entries.prediction_id
            WHERE contest_entries.contest_id = ? AND contest_entries.user_id = ? AND contest_entries.prediction_id = ?
            """,
            (contest_id, entry.user_id, entry.prediction_id),
        ).fetchone()
    return _row_to_contest_entry(row)


def list_contest_entries(contest_id: int) -> list[ContestEntry]:
    init_db()
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT contest_entries.*, users.display_name, predictions.predicted_winner, predictions.correct
            FROM contest_entries
            JOIN users ON users.id = contest_entries.user_id
            JOIN predictions ON predictions.id = contest_entries.prediction_id
            WHERE contest_entries.contest_id = ?
            ORDER BY contest_entries.created_at DESC
            """,
            (contest_id,),
        ).fetchall()
    return [_row_to_contest_entry(row) for row in rows]


def leaderboard(limit: int = 25) -> list[LeaderboardEntry]:
    init_db()
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT
                users.id AS user_id,
                users.display_name,
                COUNT(contest_entries.id) AS total_predictions,
                SUM(CASE WHEN predictions.correct IS NOT NULL THEN 1 ELSE 0 END) AS resolved_predictions,
                SUM(CASE WHEN predictions.correct = 1 THEN 1 ELSE 0 END) AS correct_predictions
            FROM users
            LEFT JOIN contest_entries ON contest_entries.user_id = users.id
            LEFT JOIN predictions ON predictions.id = contest_entries.prediction_id
            GROUP BY users.id
            ORDER BY correct_predictions DESC, resolved_predictions DESC, total_predictions DESC
            LIMIT ?
            """,
            (min(max(limit, 1), 100),),
        ).fetchall()
    return [_leaderboard_entry(row) for row in rows]


def weekly_challenges(user_id: int | None = None) -> list[WeeklyChallenge]:
    total = prediction_summary().total
    resolved = prediction_summary().resolved
    comments = 0
    follows = 0
    if user_id is not None:
        with _connect() as connection:
            comments = int(connection.execute("SELECT COUNT(*) AS count FROM comments WHERE user_id = ?", (user_id,)).fetchone()["count"])
            follows = int(connection.execute("SELECT COUNT(*) AS count FROM follows WHERE follower_id = ?", (user_id,)).fetchone()["count"])
    return [
        WeeklyChallenge(id="make-5-picks", title="Make 5 picks", description="Track five predictions this week.", target=5, progress=min(total, 5), completed=total >= 5),
        WeeklyChallenge(id="grade-3-picks", title="Grade 3 results", description="Resolve three finished predictions.", target=3, progress=min(resolved, 3), completed=resolved >= 3),
        WeeklyChallenge(id="join-conversation", title="Join the conversation", description="Comment on a game thread.", target=1, progress=min(comments, 1), completed=comments >= 1),
        WeeklyChallenge(id="follow-predictor", title="Follow a predictor", description="Follow another public profile.", target=1, progress=min(follows, 1), completed=follows >= 1),
    ]


def community_dashboard(user_id: int | None = None) -> CommunityDashboard:
    return CommunityDashboard(
        profiles=list_public_profiles(),
        leaderboard=leaderboard(limit=10),
        contests=list_contests(),
        challenges=weekly_challenges(user_id),
    )


def model_performance_report() -> ModelPerformanceReport:
    init_db()
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN correct IS NOT NULL THEN 1 ELSE 0 END) AS resolved,
                SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END) AS correct,
                SUM(CASE WHEN confidence = 'high' AND correct IS NOT NULL THEN 1 ELSE 0 END) AS high_resolved,
                SUM(CASE WHEN confidence = 'high' AND correct = 1 THEN 1 ELSE 0 END) AS high_correct,
                AVG(CASE
                    WHEN predicted_winner = home_team THEN home_win_probability
                    ELSE away_win_probability
                END) AS avg_confidence
            FROM predictions
            """
        ).fetchone()
    total = int(row["total"] or 0)
    resolved = int(row["resolved"] or 0)
    correct = int(row["correct"] or 0)
    high_resolved = int(row["high_resolved"] or 0)
    high_correct = int(row["high_correct"] or 0)
    return ModelPerformanceReport(
        total_predictions=total,
        resolved_predictions=resolved,
        accuracy=round(correct / resolved, 4) if resolved else None,
        high_confidence_accuracy=round(high_correct / high_resolved, 4) if high_resolved else None,
        average_confidence=round(float(row["avg_confidence"]), 4) if row["avg_confidence"] is not None else None,
    )


def prediction_export_rows() -> list[SavedPrediction]:
    return list_predictions(limit=100)


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _row_to_prediction(row: sqlite3.Row) -> SavedPrediction:
    values: dict[str, Any] = dict(row)
    return SavedPrediction(
        id=values["id"],
        created_at=values["created_at"],
        game_id=values["game_id"],
        sport=Sport(values["sport"]),
        game_date=values["game_date"],
        game_name=values["game_name"],
        predicted_winner=values["predicted_winner"],
        home_team=values["home_team"],
        away_team=values["away_team"],
        home_win_probability=values["home_win_probability"],
        away_win_probability=values["away_win_probability"],
        confidence=values["confidence"],
        score=values["score"],
        actual_winner=values["actual_winner"],
        correct=None if values["correct"] is None else bool(values["correct"]),
        resolved_at=values["resolved_at"],
    )


def _row_to_user(row: sqlite3.Row) -> UserProfile:
    values: dict[str, Any] = dict(row)
    return UserProfile(
        id=values["id"],
        display_name=values["display_name"],
        email=values["email"],
        created_at=values["created_at"],
        plan=Plan(values.get("plan") or "free"),
        notification_preferences=NotificationPreferences(
            daily_email=bool(values["daily_email"]),
            push_alerts=bool(values["push_alerts"]),
            close_game_alerts=bool(values["close_game_alerts"]),
        ),
    )


def _row_to_favorite(row: sqlite3.Row) -> Favorite:
    values: dict[str, Any] = dict(row)
    return Favorite(
        id=values["id"],
        user_id=values["user_id"],
        sport=Sport(values["sport"]),
        team_id=values["team_id"],
        team_name=values["team_name"],
        league_name=values["league_name"],
        created_at=values["created_at"],
    )


def _row_to_follow(row: sqlite3.Row) -> Follow:
    values: dict[str, Any] = dict(row)
    return Follow(
        id=values["id"],
        follower_id=values["follower_id"],
        following_id=values["following_id"],
        created_at=values["created_at"],
    )


def _row_to_comment(row: sqlite3.Row) -> GameComment:
    values: dict[str, Any] = dict(row)
    return GameComment(
        id=values["id"],
        user_id=values["user_id"],
        display_name=values["display_name"],
        sport=Sport(values["sport"]),
        game_id=values["game_id"],
        body=values["body"],
        created_at=values["created_at"],
    )


def _row_to_contest(row: sqlite3.Row) -> Contest:
    values: dict[str, Any] = dict(row)
    return Contest(
        id=values["id"],
        name=values["name"],
        sport=Sport(values["sport"]),
        starts_at=values["starts_at"],
        ends_at=values["ends_at"],
        created_at=values["created_at"],
    )


def _row_to_contest_entry(row: sqlite3.Row) -> ContestEntry:
    values: dict[str, Any] = dict(row)
    return ContestEntry(
        id=values["id"],
        contest_id=values["contest_id"],
        user_id=values["user_id"],
        display_name=values["display_name"],
        prediction_id=values["prediction_id"],
        predicted_winner=values["predicted_winner"],
        correct=None if values["correct"] is None else bool(values["correct"]),
        created_at=values["created_at"],
    )


def _public_profile(user_id: int) -> PublicProfile:
    with _connect() as connection:
        user = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        followers = connection.execute("SELECT COUNT(*) AS count FROM follows WHERE following_id = ?", (user_id,)).fetchone()["count"]
        following = connection.execute("SELECT COUNT(*) AS count FROM follows WHERE follower_id = ?", (user_id,)).fetchone()["count"]
        stats = connection.execute(
            """
            SELECT
                COUNT(contest_entries.id) AS total_predictions,
                SUM(CASE WHEN predictions.correct IS NOT NULL THEN 1 ELSE 0 END) AS resolved_predictions,
                SUM(CASE WHEN predictions.correct = 1 THEN 1 ELSE 0 END) AS correct_predictions
            FROM contest_entries
            LEFT JOIN predictions ON predictions.id = contest_entries.prediction_id
            WHERE contest_entries.user_id = ?
            """,
            (user_id,),
        ).fetchone()

    resolved = int(stats["resolved_predictions"] or 0)
    correct = int(stats["correct_predictions"] or 0)
    total = int(stats["total_predictions"] or 0)
    accuracy = round(correct / resolved, 4) if resolved else None
    return PublicProfile(
        id=user["id"],
        display_name=user["display_name"],
        created_at=user["created_at"],
        followers=int(followers or 0),
        following=int(following or 0),
        total_predictions=total,
        resolved_predictions=resolved,
        accuracy=accuracy,
        badges=_badges(total, resolved, correct, int(followers or 0)),
    )


def _leaderboard_entry(row: sqlite3.Row) -> LeaderboardEntry:
    values: dict[str, Any] = dict(row)
    total = int(values["total_predictions"] or 0)
    resolved = int(values["resolved_predictions"] or 0)
    correct = int(values["correct_predictions"] or 0)
    accuracy = round(correct / resolved, 4) if resolved else None
    score = correct * 3 + resolved + total * 0.25
    profile = _public_profile(values["user_id"])
    return LeaderboardEntry(
        user_id=values["user_id"],
        display_name=values["display_name"],
        total_predictions=total,
        resolved_predictions=resolved,
        correct_predictions=correct,
        accuracy=accuracy,
        score=round(score, 2),
        badges=profile.badges,
    )


def _ensure_default_contest() -> None:
    with _connect() as connection:
        count = connection.execute("SELECT COUNT(*) AS count FROM contests").fetchone()["count"]
        if count:
            return
        connection.execute(
            "INSERT INTO contests (name, sport, starts_at, ends_at, created_at) VALUES (?, ?, ?, ?, ?)",
            ("Weekly Pick'em Challenge", Sport.baseball.value, None, None, _now()),
        )


def _badges(total: int, resolved: int, correct: int, followers: int) -> list[str]:
    badges = []
    if total >= 1:
        badges.append("First Pick")
    if total >= 10:
        badges.append("Volume Picker")
    if resolved >= 5 and correct / resolved >= 0.6:
        badges.append("Sharp")
    if followers >= 3:
        badges.append("Community Voice")
    if correct >= 10:
        badges.append("Hot Streak")
    return badges


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
