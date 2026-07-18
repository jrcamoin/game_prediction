CREATE TABLE IF NOT EXISTS predictions (
  id SERIAL PRIMARY KEY,
  created_at TEXT NOT NULL,
  game_id TEXT NOT NULL,
  sport TEXT NOT NULL,
  game_date TEXT NOT NULL,
  game_name TEXT NOT NULL,
  predicted_winner TEXT NOT NULL,
  home_team TEXT NOT NULL,
  away_team TEXT NOT NULL,
  home_win_probability DOUBLE PRECISION NOT NULL,
  away_win_probability DOUBLE PRECISION NOT NULL,
  confidence TEXT NOT NULL,
  score DOUBLE PRECISION NOT NULL,
  response_json TEXT NOT NULL,
  game_json TEXT NOT NULL,
  actual_winner TEXT,
  correct INTEGER,
  resolved_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_predictions_game ON predictions (sport, game_id);

CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  display_name TEXT NOT NULL,
  email TEXT,
  created_at TEXT NOT NULL,
  plan TEXT NOT NULL DEFAULT 'free',
  daily_email INTEGER NOT NULL DEFAULT 0,
  push_alerts INTEGER NOT NULL DEFAULT 0,
  close_game_alerts INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS favorites (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  sport TEXT NOT NULL,
  team_id TEXT,
  team_name TEXT,
  league_name TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS follows (
  id SERIAL PRIMARY KEY,
  follower_id INTEGER NOT NULL,
  following_id INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(follower_id, following_id)
);

CREATE TABLE IF NOT EXISTS comments (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL,
  sport TEXT NOT NULL,
  game_id TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contests (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  sport TEXT NOT NULL,
  starts_at TEXT,
  ends_at TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contest_entries (
  id SERIAL PRIMARY KEY,
  contest_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  prediction_id INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(contest_id, user_id, prediction_id)
);
