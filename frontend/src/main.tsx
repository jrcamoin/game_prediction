import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  CalendarDays,
  Database,
  Heart,
  MessageSquare,
  Loader2,
  Moon,
  RefreshCw,
  Share2,
  Sparkles,
  Sun,
  Target,
} from "lucide-react";

import {
  addFavorite,
  addGameComment,
  createUserProfile,
  enterContest,
  fetchCommunityDashboard,
  fetchDailyFeed,
  fetchFavorites,
  fetchGameComments,
  fetchLiveGameState,
  fetchModelStatus,
  fetchPremiumAnalysis,
  fetchPremiumFeatures,
  fetchPremiumPerformance,
  fetchPremiumValuePicks,
  fetchPredictionHistory,
  fetchPredictionSummary,
  fetchRecommendedPicks,
  fetchSeasonSimulation,
  fetchUpcomingGames,
  fetchUsers,
  gradePredictionHistory,
  premiumCsvUrl,
  predictGame,
  predictLiveGame,
  removeFavorite,
  followUser,
  unfollowUser,
  upgradeToPro,
  updateNotificationPreferences,
} from "./api";
import type {
  BettingValuePick,
  CommunityDashboard,
  DailyFeed,
  DataSourceStatus,
  Favorite,
  GameComment,
  GameSnapshot,
  LiveGameState,
  LiveTeamScore,
  ModelStatus,
  NotificationPreferences,
  ModelPerformanceReport,
  PredictionRequest,
  PredictionResponse,
  PredictionSummary,
  PremiumAnalysis,
  PremiumFeatureSet,
  RecommendedPick,
  SavedPrediction,
  SeasonSimulation,
  Sport,
  TeamInput,
  UserProfile,
} from "./types";
import { ModelReadiness, SportInsight } from "./components/ModelPanels";
import { PredictionPanel } from "./components/PredictionPanel";
import "./styles.css";

const sports: Sport[] = ["football", "basketball", "baseball", "hockey", "soccer", "golf", "ufc"];

const defaultHome: TeamInput = {
  name: "Home Team",
  rating: 1545,
  recent_wins: 4,
  recent_losses: 1,
  injuries: 1,
  questionable_players: 1,
  starters_confirmed: 0,
  projected_starters: 11,
  rest_days: 4,
  moneyline: -135,
};

const defaultAway: TeamInput = {
  name: "Away Team",
  rating: 1510,
  recent_wins: 3,
  recent_losses: 2,
  injuries: 2,
  questionable_players: 1,
  starters_confirmed: 0,
  projected_starters: 11,
  rest_days: 3,
  moneyline: 115,
};

type Scenario = PredictionRequest & {
  label: string;
};

const scenarios: Scenario[] = [
  {
    label: "Balanced rivalry",
    sport: "football",
    home_team: defaultHome,
    away_team: defaultAway,
    neutral_site: false,
    home_travel_miles: 0,
    away_travel_miles: 550,
  },
  {
    label: "Road favorite",
    sport: "basketball",
    home_team: {
      name: "Metro",
      rating: 1490,
      recent_wins: 2,
      recent_losses: 3,
      injuries: 3,
      questionable_players: 1,
      starters_confirmed: 3,
      projected_starters: 5,
      rest_days: 1,
      moneyline: 145,
    },
    away_team: {
      name: "Bay City",
      rating: 1605,
      recent_wins: 5,
      recent_losses: 0,
      injuries: 1,
      questionable_players: 0,
      starters_confirmed: 5,
      projected_starters: 5,
      rest_days: 3,
      moneyline: -170,
    },
    neutral_site: false,
    home_travel_miles: 0,
    away_travel_miles: 350,
  },
  {
    label: "Neutral cup final",
    sport: "soccer",
    home_team: {
      name: "Northside",
      rating: 1560,
      recent_wins: 3,
      recent_losses: 1,
      injuries: 0,
      questionable_players: 1,
      starters_confirmed: 9,
      projected_starters: 11,
      rest_days: 5,
      moneyline: 105,
    },
    away_team: {
      name: "Harbor",
      rating: 1550,
      recent_wins: 4,
      recent_losses: 1,
      injuries: 2,
      questionable_players: 1,
      starters_confirmed: 8,
      projected_starters: 11,
      rest_days: 4,
      moneyline: 120,
    },
    neutral_site: true,
    home_travel_miles: 420,
    away_travel_miles: 390,
  },
  {
    label: "Golf head-to-head",
    sport: "golf",
    home_team: {
      name: "Player A",
      rating: 1585,
      recent_wins: 4,
      recent_losses: 1,
      injuries: 0,
      questionable_players: 0,
      starters_confirmed: 1,
      projected_starters: 1,
      rest_days: 5,
      moneyline: -125,
      expected_value_for: 1.4,
      expected_value_against: 0.8,
    },
    away_team: {
      name: "Player B",
      rating: 1540,
      recent_wins: 3,
      recent_losses: 2,
      injuries: 1,
      questionable_players: 0,
      starters_confirmed: 1,
      projected_starters: 1,
      rest_days: 5,
      moneyline: 105,
      expected_value_for: 1.1,
      expected_value_against: 1.0,
    },
    neutral_site: true,
    home_travel_miles: 700,
    away_travel_miles: 900,
  },
  {
    label: "UFC bout",
    sport: "ufc",
    home_team: {
      name: "Fighter Red",
      rating: 1600,
      recent_wins: 4,
      recent_losses: 1,
      injuries: 0,
      questionable_players: 0,
      starters_confirmed: 1,
      projected_starters: 1,
      rest_days: 7,
      moneyline: -150,
      expected_value_for: 2.2,
      expected_value_against: 1.4,
    },
    away_team: {
      name: "Fighter Blue",
      rating: 1565,
      recent_wins: 3,
      recent_losses: 2,
      injuries: 0,
      questionable_players: 1,
      starters_confirmed: 1,
      projected_starters: 1,
      rest_days: 7,
      moneyline: 130,
      expected_value_for: 1.8,
      expected_value_against: 1.7,
    },
    neutral_site: true,
    home_travel_miles: 200,
    away_travel_miles: 1200,
  },
];

function App() {
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem("game-predictor-theme") === "dark");
  const [mode, setMode] = useState<"real" | "manual">("real");
  const [sport, setSport] = useState<Sport>("football");
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [activeUserId, setActiveUserId] = useState<number | null>(() => {
    const stored = localStorage.getItem("game-predictor-user-id");
    return stored ? Number(stored) : null;
  });
  const [favorites, setFavorites] = useState<Favorite[]>([]);
  const [dailyFeed, setDailyFeed] = useState<DailyFeed | null>(null);
  const [community, setCommunity] = useState<CommunityDashboard | null>(null);
  const [premiumFeatures, setPremiumFeatures] = useState<PremiumFeatureSet | null>(null);
  const [premiumPerformance, setPremiumPerformance] = useState<ModelPerformanceReport | null>(null);
  const [valuePicks, setValuePicks] = useState<BettingValuePick[]>([]);
  const [premiumAnalysis, setPremiumAnalysis] = useState<PremiumAnalysis | null>(null);
  const [modelStatus, setModelStatus] = useState<ModelStatus | null>(null);
  const [comments, setComments] = useState<GameComment[]>([]);
  const [commentBody, setCommentBody] = useState("");
  const [seasonSimulation, setSeasonSimulation] = useState<SeasonSimulation | null>(null);
  const [liveGame, setLiveGame] = useState<LiveGameState | null>(null);
  const [liveEnabled, setLiveEnabled] = useState(true);
  const [profileName, setProfileName] = useState("");
  const [profileEmail, setProfileEmail] = useState("");
  const [historyQuery, setHistoryQuery] = useState("");
  const [historySport, setHistorySport] = useState<Sport | "all">("all");
  const [homeTeam, setHomeTeam] = useState<TeamInput>(defaultHome);
  const [awayTeam, setAwayTeam] = useState<TeamInput>(defaultAway);
  const [neutralSite, setNeutralSite] = useState(false);
  const [homeTravelMiles, setHomeTravelMiles] = useState(0);
  const [awayTravelMiles, setAwayTravelMiles] = useState(550);
  const [games, setGames] = useState<GameSnapshot[]>([]);
  const [selectedGameId, setSelectedGameId] = useState("");
  const [sourceStatuses, setSourceStatuses] = useState<DataSourceStatus[]>([]);
  const [history, setHistory] = useState<SavedPrediction[]>([]);
  const [summary, setSummary] = useState<PredictionSummary | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendedPick[]>([]);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingGames, setIsLoadingGames] = useState(false);
  const [isGrading, setIsGrading] = useState(false);

  const payload = useMemo<PredictionRequest>(
    () => ({
      sport,
      home_team: homeTeam,
      away_team: awayTeam,
      neutral_site: neutralSite,
      home_travel_miles: homeTravelMiles,
      away_travel_miles: awayTravelMiles,
    }),
    [awayTeam, awayTravelMiles, homeTeam, homeTravelMiles, neutralSite, sport],
  );

  const selectedGame = useMemo(
    () => games.find((game) => game.id === selectedGameId) ?? null,
    [games, selectedGameId],
  );
  const activeUser = users.find((user) => user.id === activeUserId) ?? null;
  const sportCapability = modelStatus?.capabilities.find((capability) => capability.sport === sport) ?? null;

  useEffect(() => {
    document.documentElement.dataset.theme = darkMode ? "dark" : "light";
    localStorage.setItem("game-predictor-theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  useEffect(() => {
    void refreshUsers();
    void refreshModelStatus();
  }, []);

  useEffect(() => {
    if (!activeUserId) {
      return;
    }
    localStorage.setItem("game-predictor-user-id", String(activeUserId));
    void refreshRetentionData(activeUserId);
    void refreshCommunity();
    void refreshPremium(activeUserId);
  }, [activeUserId]);

  useEffect(() => {
    if (mode !== "real") {
      return;
    }

    void loadUpcomingGames(sport);
  }, [mode, sport]);

  useEffect(() => {
    if (mode !== "real" || !selectedGameId || !liveEnabled) {
      setLiveGame(null);
      return;
    }

    void refreshLiveGame();
    const interval = window.setInterval(() => {
      void refreshLiveGame();
    }, 20000);
    return () => window.clearInterval(interval);
  }, [mode, sport, selectedGameId, liveEnabled]);

  useEffect(() => {
    void refreshComments();
  }, [sport, selectedGameId]);

  useEffect(() => {
    if (activeUserId) {
      void refreshPremium(activeUserId);
    }
  }, [sport, selectedGameId]);

  useEffect(() => {
    void refreshHistory();
  }, [historyQuery, historySport]);

  async function loadUpcomingGames(nextSport: Sport) {
    setIsLoadingGames(true);
    setError(null);
    setPrediction(null);
    try {
      const nextGames = await fetchUpcomingGames(nextSport);
      const nextRecommendations = await fetchRecommendedPicks(nextSport);
      const nextSimulation = await fetchSeasonSimulation(nextSport);
      setGames(nextGames);
      setRecommendations(nextRecommendations);
      setSeasonSimulation(nextSimulation);
      setSelectedGameId(nextGames[0]?.id ?? "");
      setSourceStatuses(nextGames[0]?.sources ?? []);
    } catch (err) {
      setGames([]);
      setRecommendations([]);
      setSeasonSimulation(null);
      setSelectedGameId("");
      setSourceStatuses([]);
      setError(err instanceof Error ? err.message : "Could not load real games");
    } finally {
      setIsLoadingGames(false);
    }
  }

  async function handlePredict() {
    setIsLoading(true);
    setError(null);
    try {
      if (mode === "real") {
        if (!selectedGameId) {
          throw new Error("No upcoming game is selected.");
        }
        const livePrediction = await predictLiveGame(sport, selectedGameId);
        setHomeTeam(livePrediction.game.home_team);
        setAwayTeam(livePrediction.game.away_team);
        setNeutralSite(livePrediction.game.neutral_site);
        setHomeTravelMiles(livePrediction.game.home_travel_miles);
        setAwayTravelMiles(livePrediction.game.away_travel_miles);
        setSourceStatuses(livePrediction.game.sources);
        setPrediction(livePrediction);
        if (activeUserId) {
          await refreshRetentionData(activeUserId);
        }
        await refreshHistory();
      } else {
        setPrediction(await predictGame(payload));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prediction failed");
    } finally {
      setIsLoading(false);
    }
  }

  async function refreshHistory() {
    try {
      const [nextHistory, nextSummary] = await Promise.all([
        fetchPredictionHistory(historyQuery, historySport),
        fetchPredictionSummary(),
      ]);
      setHistory(nextHistory);
      setSummary(nextSummary);
    } catch {
      setHistory([]);
      setSummary(null);
    }
  }

  async function refreshLiveGame() {
    if (!selectedGameId) {
      return;
    }
    try {
      setLiveGame(await fetchLiveGameState(sport, selectedGameId));
    } catch {
      setLiveGame(null);
    }
  }

  async function refreshUsers() {
    try {
      const nextUsers = await fetchUsers();
      setUsers(nextUsers);
      if (!activeUserId && nextUsers.length > 0) {
        setActiveUserId(nextUsers[0].id);
      }
    } catch {
      setUsers([]);
    }
  }

  async function refreshModelStatus() {
    try {
      setModelStatus(await fetchModelStatus());
    } catch {
      setModelStatus(null);
    }
  }

  async function refreshRetentionData(userId: number) {
    try {
      const [nextFavorites, nextFeed] = await Promise.all([fetchFavorites(userId), fetchDailyFeed(userId)]);
      setFavorites(nextFavorites);
      setDailyFeed(nextFeed);
    } catch {
      setFavorites([]);
      setDailyFeed(null);
    }
  }

  async function refreshCommunity() {
    try {
      setCommunity(await fetchCommunityDashboard(activeUserId));
    } catch {
      setCommunity(null);
    }
  }

  async function refreshPremium(userId: number) {
    try {
      const features = await fetchPremiumFeatures(userId);
      setPremiumFeatures(features);
      if (features.plan === "pro") {
        const [performance, picks] = await Promise.all([
          fetchPremiumPerformance(userId),
          fetchPremiumValuePicks(userId, sport),
        ]);
        setPremiumPerformance(performance);
        setValuePicks(picks);
        if (selectedGameId) {
          setPremiumAnalysis(await fetchPremiumAnalysis(userId, sport, selectedGameId));
        }
      } else {
        setPremiumPerformance(null);
        setValuePicks([]);
        setPremiumAnalysis(null);
      }
    } catch {
      setPremiumFeatures(null);
      setPremiumPerformance(null);
      setValuePicks([]);
      setPremiumAnalysis(null);
    }
  }

  async function handleUpgradeToPro() {
    if (!activeUserId) {
      setError("Create a profile before upgrading.");
      return;
    }
    const updated = await upgradeToPro(activeUserId);
    setUsers(users.map((user) => (user.id === updated.id ? updated : user)));
    await refreshPremium(activeUserId);
  }

  async function refreshComments() {
    if (!selectedGameId) {
      setComments([]);
      return;
    }
    try {
      setComments(await fetchGameComments(sport, selectedGameId));
    } catch {
      setComments([]);
    }
  }

  async function handleFollowUser(userId: number) {
    if (!activeUserId) {
      setError("Create a profile before following predictors.");
      return;
    }
    await followUser(activeUserId, userId);
    await refreshCommunity();
  }

  async function handleUnfollowUser(userId: number) {
    if (!activeUserId) {
      return;
    }
    await unfollowUser(activeUserId, userId);
    await refreshCommunity();
  }

  async function handleAddComment() {
    if (!activeUserId || !selectedGameId || !commentBody.trim()) {
      setError("Create a profile, select a game, and enter a comment.");
      return;
    }
    await addGameComment(activeUserId, sport, selectedGameId, commentBody);
    setCommentBody("");
    await refreshComments();
    await refreshCommunity();
  }

  async function handleEnterContest(contestId: number) {
    if (!activeUserId || history.length === 0) {
      setError("Create a profile and make a prediction before entering a contest.");
      return;
    }
    await enterContest(contestId, activeUserId, history[0].id);
    await refreshCommunity();
  }

  async function handleCreateProfile() {
    if (!profileName.trim()) {
      setError("Enter a display name to create a profile.");
      return;
    }
    setError(null);
    const profile = await createUserProfile(profileName, profileEmail);
    setUsers([profile, ...users]);
    setActiveUserId(profile.id);
    setProfileName("");
    setProfileEmail("");
    await refreshCommunity();
  }

  async function handleFavoriteSelectedTeam(team: "home" | "away") {
    if (!activeUserId || !selectedGame) {
      setError("Create a profile and select a real game before adding favorites.");
      return;
    }
    const selectedTeam = team === "home" ? selectedGame.home_team : selectedGame.away_team;
    await addFavorite(activeUserId, {
      sport: selectedGame.sport,
      team_id: selectedTeam.id,
      team_name: selectedTeam.name,
      league_name: titleCase(selectedGame.sport),
    });
    await refreshRetentionData(activeUserId);
  }

  async function handleRemoveFavorite(favoriteId: number) {
    if (!activeUserId) {
      return;
    }
    await removeFavorite(activeUserId, favoriteId);
    await refreshRetentionData(activeUserId);
  }

  async function handleUpdateNotifications(preferences: NotificationPreferences) {
    if (!activeUserId) {
      return;
    }
    const updated = await updateNotificationPreferences(activeUserId, preferences);
    setUsers(users.map((user) => (user.id === updated.id ? updated : user)));
  }

  async function handleGradeHistory() {
    setIsGrading(true);
    setError(null);
    try {
      await gradePredictionHistory();
      await refreshHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not grade prediction history");
    } finally {
      setIsGrading(false);
    }
  }

  function applyScenario(scenario: Scenario) {
    setSport(scenario.sport);
    setHomeTeam({ ...scenario.home_team });
    setAwayTeam({ ...scenario.away_team });
    setNeutralSite(scenario.neutral_site);
    setHomeTravelMiles(scenario.home_travel_miles);
    setAwayTravelMiles(scenario.away_travel_miles);
    setPrediction(null);
    setError(null);
    setSourceStatuses([]);
  }

  return (
    <main className="app-shell">
      <section className="hero-shell">
        <div className="topbar">
          <div className="hero-copy">
          <p className="eyebrow">Sports model workspace</p>
          <h1>Game Winner Predictor</h1>
            <p>
              Compare live matchups, inspect model drivers, and track prediction performance from one focused
              betting-research workspace.
            </p>
          </div>
          <div className="topbar-actions">
            <button className="icon-button" onClick={() => setDarkMode(!darkMode)} aria-label="Toggle dark mode">
              {darkMode ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button className="primary-button" onClick={handlePredict} disabled={isLoading}>
              {isLoading ? <Loader2 className="spin" size={18} /> : <Activity size={18} />}
              Predict
            </button>
          </div>
        </div>

        <div className="hero-metrics" aria-label="Workspace summary">
          <Metric label="Mode" value={mode === "real" ? "Live games" : "Manual"} />
          <Metric label="Profile" value={activeUser?.display_name ?? "Guest"} />
          <Metric label="Selected" value={selectedGame?.name ?? `${awayTeam.name} at ${homeTeam.name}`} />
          <Metric label="Tracked" value={String(summary?.total ?? 0)} />
        </div>
      </section>

      <nav className="product-nav" aria-label="Primary sections">
        <a href="#predict">Predict</a>
        <a href="#sports">Sports</a>
        <a href="#account">Account</a>
        <a href="#premium">Model</a>
        <a href="#community">Community</a>
        <a href="#history">History</a>
      </nav>

      <section id="sports" className="intelligence-grid">
        <SportInsight sport={sport} capability={sportCapability} />
        <ModelReadiness status={modelStatus} capability={sportCapability} onRefresh={refreshModelStatus} />
      </section>

      <section id="predict" className="workspace">
        <div className="input-panel">
          <div className="mode-tabs" role="tablist" aria-label="Prediction mode">
            <button className={mode === "real" ? "active" : ""} type="button" onClick={() => setMode("real")}>
              <Database size={16} />
              Real games
            </button>
            <button className={mode === "manual" ? "active" : ""} type="button" onClick={() => setMode("manual")}>
              <Activity size={16} />
              Manual
            </button>
          </div>

          <div className="panel-header">
            <div>
              <p className="eyebrow">Matchup setup</p>
              <h2>{mode === "real" ? "Live data matchup" : "Game inputs"}</h2>
            </div>
            {mode === "real" ? (
              <button className="secondary-button" onClick={() => loadUpcomingGames(sport)} disabled={isLoadingGames}>
                {isLoadingGames ? <Loader2 className="spin" size={16} /> : <RefreshCw size={16} />}
                Refresh
              </button>
            ) : (
              <button className="secondary-button" onClick={() => applyScenario(scenarios[0])}>
                <RefreshCw size={16} />
                Reset
              </button>
            )}
          </div>

          {mode === "manual" ? (
            <div className="scenario-row" aria-label="Scenario presets">
              {scenarios.map((scenario) => (
                <button key={scenario.label} type="button" onClick={() => applyScenario(scenario)}>
                  <Sparkles size={15} />
                  {scenario.label}
                </button>
              ))}
            </div>
          ) : null}

          <div className="field-group">
            <label htmlFor="sport">Sport</label>
            <select
              id="sport"
              value={sport}
              onChange={(event) => {
                const nextSport = event.target.value as Sport;
                const nextCapability = modelStatus?.capabilities.find((capability) => capability.sport === nextSport);
                setSport(nextSport);
                if (nextCapability && !nextCapability.live_schedule) {
                  setMode("manual");
                }
                setPrediction(null);
              }}
            >
              {sports.map((item) => (
                <option key={item} value={item}>
                  {titleCase(item)}
                </option>
              ))}
            </select>
          </div>

          {mode === "real" ? (
            <RealGameSelector
              games={games}
              recommendations={recommendations}
              selectedGameId={selectedGameId}
              isLoading={isLoadingGames}
              selectedGame={selectedGame}
              liveEnabled={liveEnabled}
              onToggleLive={setLiveEnabled}
              onChange={(gameId) => {
                const nextGame = games.find((game) => game.id === gameId);
                setSelectedGameId(gameId);
                setSourceStatuses(nextGame?.sources ?? []);
                setPrediction(null);
              }}
            />
          ) : (
            <>
              <div className="teams-grid">
                <TeamForm title="Home" team={homeTeam} onChange={setHomeTeam} />
                <TeamForm title="Away" team={awayTeam} onChange={setAwayTeam} />
              </div>

              <div className="settings-row">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={neutralSite}
                    onChange={(event) => setNeutralSite(event.target.checked)}
                  />
                  Neutral site
                </label>
                <NumberField label="Home travel" value={homeTravelMiles} onChange={setHomeTravelMiles} min={0} max={10000} />
                <NumberField label="Away travel" value={awayTravelMiles} onChange={setAwayTravelMiles} min={0} max={10000} />
              </div>
            </>
          )}
        </div>

        <PredictionPanel
          prediction={prediction}
          error={error}
          homeTeam={homeTeam.name}
          awayTeam={awayTeam.name}
          sources={sourceStatuses}
        />
      </section>

      <AccountPanel
        users={users}
        activeUser={activeUser}
        activeUserId={activeUserId}
        profileName={profileName}
        profileEmail={profileEmail}
        favorites={favorites}
        selectedGame={selectedGame}
        dailyFeed={dailyFeed}
        onSelectUser={setActiveUserId}
        onNameChange={setProfileName}
        onEmailChange={setProfileEmail}
        onCreateProfile={handleCreateProfile}
        onFavoriteTeam={handleFavoriteSelectedTeam}
        onRemoveFavorite={handleRemoveFavorite}
        onUpdateNotifications={handleUpdateNotifications}
      />

      <PremiumPanel
        activeUser={activeUser}
        features={premiumFeatures}
        performance={premiumPerformance}
        valuePicks={valuePicks}
        analysis={premiumAnalysis}
        onUpgrade={handleUpgradeToPro}
      />

      <CommunityPanel
        community={community}
        activeUserId={activeUserId}
        comments={comments}
        commentBody={commentBody}
        selectedGame={selectedGame}
        history={history}
        onCommentChange={setCommentBody}
        onAddComment={handleAddComment}
        onFollow={handleFollowUser}
        onUnfollow={handleUnfollowUser}
        onEnterContest={handleEnterContest}
        onRefresh={refreshCommunity}
      />

      <SimulationPanel simulation={seasonSimulation} />

      <LiveCompanionPanel liveGame={liveGame} onRefresh={refreshLiveGame} />

      <HistoryPanel
        history={history}
        summary={summary}
        query={historyQuery}
        sport={historySport}
        isGrading={isGrading}
        onQueryChange={setHistoryQuery}
        onSportChange={setHistorySport}
        onGrade={handleGradeHistory}
        onRefresh={refreshHistory}
      />
    </main>
  );
}

function SimulationPanel({ simulation }: { simulation: SeasonSimulation | null }) {
  if (!simulation || simulation.teams.length === 0) {
    return null;
  }

  return (
    <section className="simulation-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Season simulation</p>
          <h2>{titleCase(simulation.sport)} outlook</h2>
        </div>
        <span>{simulation.simulations.toLocaleString()} runs · {simulation.remaining_games} games</span>
      </div>
      <div className="simulation-list">
        {simulation.teams.slice(0, 8).map((team) => (
          <div key={team.team}>
            <strong>{team.playoff_seed}. {team.team}</strong>
            <span>{team.expected_wins.toFixed(1)} expected wins</span>
            <em>{team.simulated_wins} avg simulated</em>
          </div>
        ))}
      </div>
    </section>
  );
}

function PremiumPanel({
  activeUser,
  features,
  performance,
  valuePicks,
  analysis,
  onUpgrade,
}: {
  activeUser: UserProfile | null;
  features: PremiumFeatureSet | null;
  performance: ModelPerformanceReport | null;
  valuePicks: BettingValuePick[];
  analysis: PremiumAnalysis | null;
  onUpgrade: () => void;
}) {
  const isPro = features?.plan === "pro";
  return (
    <section id="premium" className="premium-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Premium</p>
          <h2>{isPro ? "Pro analytics unlocked" : "Power-user tools"}</h2>
        </div>
        {isPro && activeUser ? (
          <a className="secondary-link" href={premiumCsvUrl(activeUser.id)}>
            Download CSV
          </a>
        ) : (
          <button className="primary-button" type="button" onClick={onUpgrade}>
            Upgrade to Pro
          </button>
        )}
      </div>

      <div className="premium-grid">
        <div className="premium-card">
          <p className="eyebrow">Plan</p>
          <strong>{features?.plan === "pro" ? "Pro" : "Free"}</strong>
          <span>{isPro ? "Unlimited analysis, premium models, CSV export, value analytics, ad-free." : "Upgrade to unlock advanced model tooling and exports."}</span>
        </div>

        <div className="premium-card">
          <p className="eyebrow">Model performance</p>
          <strong>{performance?.accuracy === null || !performance ? "N/A" : `${Math.round(performance.accuracy * 100)}% accuracy`}</strong>
          <span>{performance ? `${performance.resolved_predictions}/${performance.total_predictions} resolved · high confidence ${performance.high_confidence_accuracy === null ? "N/A" : `${Math.round(performance.high_confidence_accuracy * 100)}%`}` : "Available on Pro."}</span>
        </div>

        <div className="premium-card premium-analysis-card">
          <p className="eyebrow">Premium analysis</p>
          <strong>{analysis?.headline ?? "Select a real game"}</strong>
          <span>{analysis?.model_edge_summary ?? "Pro analysis adds risk factors, watch points, and value context."}</span>
          {analysis ? (
            <ul>
              {analysis.risk_factors.map((risk) => (
                <li key={risk}>{risk}</li>
              ))}
            </ul>
          ) : null}
        </div>

        <div className="premium-card">
          <p className="eyebrow">Value analytics</p>
          <div className="value-list">
            {valuePicks.length ? (
              valuePicks.slice(0, 4).map((pick) => (
                <div key={pick.game_id}>
                  <strong>{pick.predicted_winner}</strong>
                  <span>{pick.edge === null ? "No odds" : `${Math.round(pick.edge * 100)} pt edge`} · {pick.game_name}</span>
                </div>
              ))
            ) : (
              <span>{isPro ? "No positive value edges available from current odds." : "Available on Pro when odds are configured."}</span>
            )}
          </div>
        </div>
      </div>
      <small className="premium-disclaimer">
        Betting analytics are informational only and not financial advice. Use only where legal.
      </small>
    </section>
  );
}

type CommunityPanelProps = {
  community: CommunityDashboard | null;
  activeUserId: number | null;
  comments: GameComment[];
  commentBody: string;
  selectedGame: GameSnapshot | null;
  history: SavedPrediction[];
  onCommentChange: (value: string) => void;
  onAddComment: () => void;
  onFollow: (userId: number) => void;
  onUnfollow: (userId: number) => void;
  onEnterContest: (contestId: number) => void;
  onRefresh: () => void;
};

function CommunityPanel({
  community,
  activeUserId,
  comments,
  commentBody,
  selectedGame,
  history,
  onCommentChange,
  onAddComment,
  onFollow,
  onUnfollow,
  onEnterContest,
  onRefresh,
}: CommunityPanelProps) {
  return (
    <section id="community" className="community-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Community</p>
          <h2>Predictor network</h2>
        </div>
        <button className="secondary-button" type="button" onClick={onRefresh}>
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      <div className="community-grid">
        <div className="community-card">
          <p className="eyebrow">Leaderboard</p>
          <div className="leaderboard-list">
            {community?.leaderboard.length ? (
              community.leaderboard.map((entry, index) => (
                <div key={entry.user_id}>
                  <strong>{index + 1}. {entry.display_name}</strong>
                  <span>{entry.score.toFixed(1)} pts · {entry.accuracy === null ? "N/A" : `${Math.round(entry.accuracy * 100)}%`}</span>
                  <em>{entry.badges[0] ?? "Rookie"}</em>
                </div>
              ))
            ) : (
              <p>No contest entries yet.</p>
            )}
          </div>
        </div>

        <div className="community-card">
          <p className="eyebrow">Public profiles</p>
          <div className="profile-list">
            {community?.profiles.length ? (
              community.profiles.map((profile) => (
                <div key={profile.id}>
                  <strong>{profile.display_name}</strong>
                  <span>{profile.followers} followers · {profile.badges.join(", ") || "No badges yet"}</span>
                  {activeUserId && activeUserId !== profile.id ? (
                    <div className="inline-actions">
                      <button type="button" onClick={() => onFollow(profile.id)}>Follow</button>
                      <button type="button" onClick={() => onUnfollow(profile.id)}>Unfollow</button>
                    </div>
                  ) : null}
                </div>
              ))
            ) : (
              <p>Create a profile to appear here.</p>
            )}
          </div>
        </div>

        <div className="community-card">
          <p className="eyebrow">Weekly challenges</p>
          <div className="challenge-list">
            {community?.challenges.map((challenge) => (
              <div key={challenge.id}>
                <strong>{challenge.title}</strong>
                <span>{challenge.description}</span>
                <progress value={challenge.progress} max={challenge.target} />
              </div>
            ))}
          </div>
        </div>

        <div className="community-card">
          <p className="eyebrow">Contests</p>
          <div className="contest-list">
            {community?.contests.map((contest) => (
              <div key={contest.id}>
                <strong>{contest.name}</strong>
                <span>{titleCase(contest.sport)} · enter latest saved pick</span>
                <button type="button" onClick={() => onEnterContest(contest.id)} disabled={history.length === 0}>
                  Enter
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="community-card comments-card">
          <p className="eyebrow">Game comments</p>
          <h3>{selectedGame?.name ?? "Select a game"}</h3>
          <div className="comment-form">
            <input value={commentBody} onChange={(event) => onCommentChange(event.target.value)} placeholder="Add a comment" />
            <button className="secondary-button" type="button" onClick={onAddComment}>
              <MessageSquare size={16} />
              Post
            </button>
          </div>
          <div className="comment-list">
            {comments.length ? (
              comments.map((comment) => (
                <div key={comment.id}>
                  <strong>{comment.display_name}</strong>
                  <span>{comment.body}</span>
                </div>
              ))
            ) : (
              <p>No comments yet.</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function LiveCompanionPanel({ liveGame, onRefresh }: { liveGame: LiveGameState | null; onRefresh: () => void }) {
  if (!liveGame) {
    return null;
  }

  return (
    <section className="live-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Live companion</p>
          <h2>{liveGame.name}</h2>
        </div>
        <button className="secondary-button" type="button" onClick={onRefresh}>
          <RefreshCw size={16} />
          Refresh live
        </button>
      </div>

      <div className="live-scoreboard">
        <TeamScore team={liveGame.away_team} />
        <div className="game-status">
          <strong>{liveGame.status}</strong>
          <span>{liveGame.period ?? ""} {liveGame.clock ?? ""}</span>
          <em>{liveGame.predicted_winner} {Math.round((liveGame.predicted_winner === liveGame.home_team.name ? liveGame.home_win_probability : 1 - liveGame.home_win_probability) * 100)}%</em>
        </div>
        <TeamScore team={liveGame.home_team} />
      </div>

      <div className="live-grid">
        <div className="live-card">
          <p className="eyebrow">Win probability</p>
          <LineChart points={liveGame.win_probability.map((point) => point.home_win_probability)} />
        </div>
        <div className="live-card">
          <p className="eyebrow">Momentum</p>
          <BarChart values={liveGame.momentum.map((point) => point.home_momentum)} />
        </div>
      </div>

      <div className="live-grid">
        <div className="live-card">
          <p className="eyebrow">Event timeline</p>
          <div className="timeline-list">
            {liveGame.timeline.slice().reverse().map((event) => (
              <div key={event.id} className={event.scoring_play ? "scoring-event" : ""}>
                <span>{event.period ?? "Game"} · {event.away_score}-{event.home_score}</span>
                <strong>{event.text}</strong>
              </div>
            ))}
          </div>
        </div>
        <div className="live-card">
          <p className="eyebrow">Expected updates</p>
          <div className="expected-list">
            {liveGame.expected_updates.map((update) => (
              <span key={update}>{update}</span>
            ))}
          </div>
          <p className="eyebrow stat-heading">Player stats</p>
          <div className="player-stat-list">
            {liveGame.player_stats.length ? (
              liveGame.player_stats.slice(0, 8).map((stat) => (
                <div key={`${stat.team}-${stat.player}-${stat.stat_line}`}>
                  <strong>{stat.player}</strong>
                  <span>{stat.team} · {stat.stat_line}</span>
                </div>
              ))
            ) : (
              <span>Player stats unavailable for this game state.</span>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function TeamScore({ team }: { team: LiveTeamScore }) {
  return (
    <div className="team-score">
      <span>{team.home_away.toUpperCase()}</span>
      <strong>{team.abbreviation ?? team.name}</strong>
      <em>{team.score}</em>
      {team.record ? <small>{team.record}</small> : null}
    </div>
  );
}

function LineChart({ points }: { points: number[] }) {
  const values = points.length ? points : [0.5];
  const width = 320;
  const height = 120;
  const path = values
    .map((value, index) => {
      const x = values.length === 1 ? 0 : (index / (values.length - 1)) * width;
      const y = height - value * height;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg className="chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Live win probability chart">
      <line x1="0" x2={width} y1={height / 2} y2={height / 2} />
      <path d={path} />
    </svg>
  );
}

function BarChart({ values }: { values: number[] }) {
  const width = 320;
  const height = 120;
  const visible = values.length ? values.slice(-24) : [0];
  const barWidth = width / visible.length;
  return (
    <svg className="chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Live momentum chart">
      <line x1="0" x2={width} y1={height / 2} y2={height / 2} />
      {visible.map((value, index) => {
        const capped = Math.max(-20, Math.min(20, value));
        const barHeight = Math.abs(capped) * 2.5;
        const y = capped >= 0 ? height / 2 - barHeight : height / 2;
        return <rect key={`${index}-${value}`} x={index * barWidth + 1} y={y} width={Math.max(2, barWidth - 2)} height={Math.max(2, barHeight)} />;
      })}
    </svg>
  );
}

type HistoryPanelProps = {
  history: SavedPrediction[];
  summary: PredictionSummary | null;
  query: string;
  sport: Sport | "all";
  isGrading: boolean;
  onQueryChange: (query: string) => void;
  onSportChange: (sport: Sport | "all") => void;
  onGrade: () => void;
  onRefresh: () => void;
};

function HistoryPanel({
  history,
  summary,
  query,
  sport,
  isGrading,
  onQueryChange,
  onSportChange,
  onGrade,
  onRefresh,
}: HistoryPanelProps) {
  return (
    <section id="history" className="history-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Tracking</p>
          <h2>Prediction history</h2>
        </div>
        <div className="history-actions">
          <button className="secondary-button" type="button" onClick={onRefresh}>
            <RefreshCw size={16} />
            Refresh
          </button>
          <button className="secondary-button" type="button" onClick={onGrade} disabled={isGrading}>
            {isGrading ? <Loader2 className="spin" size={16} /> : <Target size={16} />}
            Grade finished games
          </button>
        </div>
      </div>

      <div className="summary-grid">
        <Metric label="Tracked" value={String(summary?.total ?? 0)} />
        <Metric label="Pending" value={String(summary?.pending ?? 0)} />
        <Metric label="Resolved" value={String(summary?.resolved ?? 0)} />
        <Metric label="Accuracy" value={summary?.accuracy === null || !summary ? "N/A" : `${Math.round(summary.accuracy * 100)}%`} />
      </div>

      <div className="history-filters">
        <input placeholder="Search predictions" value={query} onChange={(event) => onQueryChange(event.target.value)} />
        <select value={sport} onChange={(event) => onSportChange(event.target.value as Sport | "all")}>
          <option value="all">All sports</option>
          {sports.map((item) => (
            <option key={item} value={item}>
              {titleCase(item)}
            </option>
          ))}
        </select>
      </div>

      <div className="history-list">
        {history.length === 0 ? (
          <p className="empty-history">Run a real-game prediction to start tracking performance.</p>
        ) : (
          history.map((item) => <HistoryItem key={item.id} item={item} />)
        )}
      </div>
    </section>
  );
}

function HistoryItem({ item }: { item: SavedPrediction }) {
  const status = item.correct === null ? "Pending" : item.correct ? "Correct" : "Missed";
  const probability =
    item.predicted_winner === item.home_team ? item.home_win_probability : item.away_win_probability;

  return (
    <article className="history-item">
      <div>
        <span>{formatGameDate(item.game_date)}</span>
        <strong>{item.game_name}</strong>
      </div>
      <div>
        <span>Pick</span>
        <strong>
          {item.predicted_winner} · {Math.round(probability * 100)}%
        </strong>
      </div>
      <div>
        <span>Result</span>
        <strong className={item.correct === null ? "" : item.correct ? "positive" : "negative"}>
          {item.actual_winner ? `${status}: ${item.actual_winner}` : status}
        </strong>
      </div>
      <button className="icon-button" type="button" onClick={() => sharePrediction(item)} aria-label="Share prediction">
        <Share2 size={16} />
      </button>
    </article>
  );
}

type AccountPanelProps = {
  users: UserProfile[];
  activeUser: UserProfile | null;
  activeUserId: number | null;
  profileName: string;
  profileEmail: string;
  favorites: Favorite[];
  selectedGame: GameSnapshot | null;
  dailyFeed: DailyFeed | null;
  onSelectUser: (userId: number) => void;
  onNameChange: (value: string) => void;
  onEmailChange: (value: string) => void;
  onCreateProfile: () => void;
  onFavoriteTeam: (team: "home" | "away") => void;
  onRemoveFavorite: (favoriteId: number) => void;
  onUpdateNotifications: (preferences: NotificationPreferences) => void;
};

function AccountPanel({
  users,
  activeUser,
  activeUserId,
  profileName,
  profileEmail,
  favorites,
  selectedGame,
  dailyFeed,
  onSelectUser,
  onNameChange,
  onEmailChange,
  onCreateProfile,
  onFavoriteTeam,
  onRemoveFavorite,
  onUpdateNotifications,
}: AccountPanelProps) {
  return (
    <section id="account" className="retention-grid">
      <div className="account-card">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Profile</p>
            <h2>{activeUser ? activeUser.display_name : "Create account"}</h2>
          </div>
          {users.length > 0 ? (
            <select value={activeUserId ?? ""} onChange={(event) => onSelectUser(Number(event.target.value))}>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.display_name}
                </option>
              ))}
            </select>
          ) : null}
        </div>

        {!activeUser ? (
          <div className="profile-form">
            <input placeholder="Display name" value={profileName} onChange={(event) => onNameChange(event.target.value)} />
            <input placeholder="Email optional" value={profileEmail} onChange={(event) => onEmailChange(event.target.value)} />
            <button className="secondary-button" type="button" onClick={onCreateProfile}>
              Create profile
            </button>
          </div>
        ) : (
          <div className="notification-toggles">
            <Toggle
              label="Daily email"
              checked={activeUser.notification_preferences.daily_email}
              onChange={(checked) => onUpdateNotifications({ ...activeUser.notification_preferences, daily_email: checked })}
            />
            <Toggle
              label="Push alerts"
              checked={activeUser.notification_preferences.push_alerts}
              onChange={(checked) => onUpdateNotifications({ ...activeUser.notification_preferences, push_alerts: checked })}
            />
            <Toggle
              label="Close game alerts"
              checked={activeUser.notification_preferences.close_game_alerts}
              onChange={(checked) => onUpdateNotifications({ ...activeUser.notification_preferences, close_game_alerts: checked })}
            />
          </div>
        )}
      </div>

      <div className="account-card">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Favorites</p>
            <h2>Teams and leagues</h2>
          </div>
        </div>
        {selectedGame ? (
          <div className="favorite-actions">
            <button className="secondary-button" type="button" onClick={() => onFavoriteTeam("away")}>
              <Heart size={16} />
              {selectedGame.away_team.abbreviation ?? selectedGame.away_team.name}
            </button>
            <button className="secondary-button" type="button" onClick={() => onFavoriteTeam("home")}>
              <Heart size={16} />
              {selectedGame.home_team.abbreviation ?? selectedGame.home_team.name}
            </button>
          </div>
        ) : null}
        <div className="favorite-list">
          {favorites.length === 0 ? (
            <p>No favorites yet.</p>
          ) : (
            favorites.map((favorite) => (
              <button key={favorite.id} type="button" onClick={() => onRemoveFavorite(favorite.id)}>
                {favorite.team_name ?? favorite.league_name ?? titleCase(favorite.sport)}
              </button>
            ))
          )}
        </div>
      </div>

      <div className="account-card daily-card">
        <p className="eyebrow">Daily feed</p>
        <h2>Best picks for you</h2>
        <div className="feed-list">
          {dailyFeed?.picks.length ? (
            dailyFeed.picks.slice(0, 4).map((pick) => (
              <div key={`${pick.sport}-${pick.game_id}`}>
                <span>{formatGameDate(pick.game_date)}</span>
                <strong>{pick.predicted_winner}</strong>
                <em>{Math.round(pick.probability * 100)}%</em>
              </div>
            ))
          ) : (
            <p>Create favorites to personalize this feed.</p>
          )}
        </div>
      </div>
    </section>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="toggle-row">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      {label}
    </label>
  );
}

type RealGameSelectorProps = {
  games: GameSnapshot[];
  recommendations: RecommendedPick[];
  selectedGameId: string;
  selectedGame: GameSnapshot | null;
  isLoading: boolean;
  liveEnabled: boolean;
  onToggleLive: (enabled: boolean) => void;
  onChange: (gameId: string) => void;
};

function RealGameSelector({
  games,
  recommendations,
  selectedGameId,
  selectedGame,
  isLoading,
  liveEnabled,
  onToggleLive,
  onChange,
}: RealGameSelectorProps) {
  return (
    <div className="real-data-panel">
      <div className="field-group">
        <label htmlFor="game">Upcoming game</label>
        <select id="game" value={selectedGameId} onChange={(event) => onChange(event.target.value)} disabled={isLoading}>
          {games.length === 0 ? <option value="">No upcoming games loaded</option> : null}
          {games.map((game) => (
            <option key={game.id} value={game.id}>
              {formatGameDate(game.date)} - {game.name}
            </option>
          ))}
        </select>
      </div>

      {selectedGame ? (
        <div className="game-preview">
          <div>
            <span>Away</span>
            <strong>{selectedGame.away_team.name}</strong>
            <small>Rating {selectedGame.away_team.rating}</small>
          </div>
          <CalendarDays size={20} />
          <div>
            <span>Home</span>
            <strong>{selectedGame.home_team.name}</strong>
            <small>Rating {selectedGame.home_team.rating}</small>
          </div>
        </div>
      ) : null}

      <label className="toggle-row">
        <input type="checkbox" checked={liveEnabled} onChange={(event) => onToggleLive(event.target.checked)} />
        Live companion polling
      </label>

      {recommendations.length > 0 ? (
        <div className="recommendation-list">
          <p className="eyebrow">Top upcoming picks</p>
          {recommendations.map((pick) => (
            <button key={pick.game_id} type="button" onClick={() => onChange(pick.game_id)}>
              <span>{formatGameDate(pick.game_date)}</span>
              <strong>{pick.predicted_winner}</strong>
              <em>{Math.round(pick.probability * 100)}%</em>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

type TeamFormProps = {
  title: string;
  team: TeamInput;
  onChange: (team: TeamInput) => void;
};

function TeamForm({ title, team, onChange }: TeamFormProps) {
  const update = <K extends keyof TeamInput>(key: K, value: TeamInput[K]) => {
    onChange({ ...team, [key]: value });
  };

  return (
    <div className="team-card">
      <h2>{title}</h2>
      <div className="field-group">
        <label htmlFor={`${title}-name`}>Team name</label>
        <input id={`${title}-name`} value={team.name} onChange={(event) => update("name", event.target.value)} />
      </div>
      <div className="field-grid">
        <NumberField label="Rating" value={team.rating} onChange={(value) => update("rating", value)} min={1000} max={2200} />
        <NumberField label="Recent wins" value={team.recent_wins} onChange={(value) => update("recent_wins", value)} min={0} max={10} />
        <NumberField label="Recent losses" value={team.recent_losses} onChange={(value) => update("recent_losses", value)} min={0} max={10} />
        <NumberField label="Injuries" value={team.injuries} onChange={(value) => update("injuries", value)} min={0} max={20} />
        <NumberField label="Questionable" value={team.questionable_players} onChange={(value) => update("questionable_players", value)} min={0} max={20} />
        <NumberField label="Starters confirmed" value={team.starters_confirmed} onChange={(value) => update("starters_confirmed", value)} min={0} max={30} />
        <NumberField label="Projected starters" value={team.projected_starters} onChange={(value) => update("projected_starters", value)} min={1} max={30} />
        <NumberField label="Rest days" value={team.rest_days} onChange={(value) => update("rest_days", value)} min={0} max={14} />
        <NumberField
          label="Moneyline"
          value={team.moneyline ?? 0}
          onChange={(value) => update("moneyline", value === 0 ? null : value)}
          min={-5000}
          max={5000}
        />
        <NumberField
          label="Expected value for"
          value={team.expected_value_for ?? 0}
          onChange={(value) => update("expected_value_for", value === 0 ? null : value)}
          min={0}
          max={20}
          step={0.1}
        />
        <NumberField
          label="Expected value against"
          value={team.expected_value_against ?? 0}
          onChange={(value) => update("expected_value_against", value === 0 ? null : value)}
          min={0}
          max={20}
          step={0.1}
        />
      </div>
    </div>
  );
}

type NumberFieldProps = {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
};

function NumberField({ label, value, onChange, min, max, step = 1 }: NumberFieldProps) {
  const id = label.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className="field-group">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function titleCase(value: string) {
  return value.replace(/\w\S*/g, (text) => text.charAt(0).toUpperCase() + text.slice(1).toLowerCase());
}

function formatGameDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

async function sharePrediction(item: SavedPrediction) {
  const probability = item.predicted_winner === item.home_team ? item.home_win_probability : item.away_win_probability;
  const text = `${item.game_name}: ${item.predicted_winner} at ${Math.round(probability * 100)}% on Game Winner Predictor`;
  if (navigator.share) {
    await navigator.share({ title: "Game prediction", text });
    return;
  }
  await navigator.clipboard.writeText(text);
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
