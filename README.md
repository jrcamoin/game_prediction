<<<<<<< HEAD
# game_prediction
Webapp to predict upcoming sporting events
=======
# Sports Game Winner Predictor

Initial codebase for a web app that predicts likely winners of sports games.

The app has:

- `backend/`: FastAPI service with a prediction endpoint.
- `frontend/`: React + Vite UI for entering game inputs and viewing predictions.
- Live-game mode with ESPN-backed schedules, recent form, generated ratings, top picks, and saved prediction tracking.
- Retention features: local profiles, favorite teams/leagues, a personalized daily feed, notification preferences, searchable history, dark mode, and shareable predictions.
- Smarter prediction features: ensemble model output, calibrated confidence, feature importance, lineup/injury context, optional venue weather, advanced ratings, and season simulations.
- Live second-screen experience: live score polling, in-game win probability, momentum, event timeline, player stats, and expected points/runs notes from ESPN live summary data.
- Community features: public profiles, following, game comments, weekly contests, leaderboard scoring, challenges, badges, and achievements.
- Premium prototype features: Pro plan flag, premium analysis, historical model performance, CSV export, value analytics when odds are configured, and ad-free/premium feature gates.

The first model is intentionally transparent and deterministic. It combines team rating, recent form, injuries, rest days, home field, travel, and optional market odds into a win probability. This is a practical baseline that can later be replaced or calibrated with historical game data.

The app can also build predictions from real upcoming games. It uses ESPN scoreboard data for schedules, teams, scores, venue flags, and recent results. If `ODDS_API_KEY` is set, it also attempts to merge head-to-head moneyline odds from The Odds API.

Outdoor live-game predictions attempt to enrich selected games with venue weather from Open-Meteo when ESPN venue location data can be geocoded.

## Requirements

- Python 3.11+
- Node.js 20+

## Run The Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs will be available at `http://localhost:8000/docs`.

### Optional Odds Source

```bash
export ODDS_API_KEY=your_api_key
export ODDS_REGIONS=us
```

Without an odds key, live predictions still work from ESPN data and the market factor remains neutral.

## Test The Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest tests
```

## Run The Frontend

```bash
cd frontend
npm install
npm start
```

The frontend runs at `http://localhost:5173` and calls the backend at `http://localhost:8000`.

Build the frontend with:

```bash
cd frontend
npm run build
```

## Useful Endpoints

- `GET /health`
- `GET /api/games/upcoming?sport=baseball&days=14`
- `GET /api/games/recommendations?sport=baseball&days=14&limit=5`
- `POST /api/predict`
- `POST /api/predict/batch`
- `POST /api/predict/live/{sport}/{game_id}`
- `GET /api/predictions`
- `GET /api/predictions/summary`
- `POST /api/predictions/grade`
- `GET /api/games/result/{sport}/{game_id}`
- `GET /api/users`
- `POST /api/users`
- `GET /api/users/{user_id}/daily-feed`
- `GET /api/users/{user_id}/favorites`
- `POST /api/users/{user_id}/favorites`
- `PUT /api/users/{user_id}/notifications`
- `GET /api/simulations/season?sport=baseball&days=30&simulations=1000`
- `GET /api/live/{sport}/{game_id}`
- `GET /api/community`
- `GET /api/community/profiles`
- `POST /api/community/follows`
- `GET /api/community/comments/{sport}/{game_id}`
- `POST /api/community/comments`
- `GET /api/community/contests`
- `POST /api/community/contests/{contest_id}/entries`
- `GET /api/community/leaderboard`
- `GET /api/community/challenges`
- `GET /api/premium/features/{user_id}`
- `POST /api/premium/upgrade/{user_id}`
- `GET /api/premium/performance?user_id={user_id}`
- `GET /api/premium/value-picks?user_id={user_id}&sport=baseball`
- `GET /api/premium/analysis/{sport}/{game_id}?user_id={user_id}`
- `GET /api/premium/export/predictions.csv?user_id={user_id}`

## Retention Notes

Profiles, favorites, notification preferences, and prediction history are stored in local SQLite at `backend/data/game_predictor.sqlite3` by default. Set `GAME_PREDICTOR_DB` to use a different path.

Email and push notifications are currently preference-tracking only. Real delivery should be connected after choosing a production auth, email, and push provider.

Community features are local-prototype features backed by SQLite. Production community launch needs real authentication, moderation tools, anti-spam controls, and privacy settings before exposing comments or public profiles broadly.

Premium features are local plan-gated prototypes. Production monetization needs a billing provider, entitlement checks on every protected route, usage limits, invoices, cancellation flows, and terms/compliance review. Betting value analytics is informational only and should only be shown where legally appropriate.

## Next Steps

- Add user accounts, saved leagues, and cloud-hosted persistence.
- Replace local profiles with production authentication.
- Connect real email and push notification delivery.
- Calibrate sport-specific Elo weights against historical results.
- Add a dedicated injuries/lineups source and travel-distance calculation.
- Train sport-specific models and calibrate probabilities.
<<<<<<< HEAD
- Add authentication and saved leagues.
>>>>>>> d626e53 (Initial sports prediction webapp)
=======
- Add closing-line value and sportsbook comparison views when odds are configured.
- Replace fallback live win probability with sport-specific trained in-game models.
- Add a dedicated xG/xPoints provider for sports where ESPN does not expose expected-value data.
- Add production moderation, blocking/reporting, and private profile controls for community features.
- Integrate Stripe or another billing provider for real premium subscriptions.
- Add server-side usage limits for free users and audit logging for premium entitlement checks.
>>>>>>> 6676c6b (initial commit to the game predictor app, phase 1-6)
