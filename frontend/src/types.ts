export type Sport = "football" | "basketball" | "baseball" | "hockey" | "soccer";
export type Plan = "free" | "pro";

export type TeamInput = {
  name: string;
  rating: number;
  recent_wins: number;
  recent_losses: number;
  injuries: number;
  questionable_players: number;
  starters_confirmed: number;
  projected_starters: number;
  rest_days: number;
  moneyline: number | null;
};

export type PredictionRequest = {
  sport: Sport;
  home_team: TeamInput;
  away_team: TeamInput;
  neutral_site: boolean;
  home_travel_miles: number;
  away_travel_miles: number;
  weather?: WeatherSnapshot | null;
};

export type ModelPrediction = {
  name: string;
  home_win_probability: number;
  weight: number;
};

export type FeatureImportance = {
  name: string;
  value: number;
  impact: number;
  direction: "home" | "away" | "neutral";
};

export type WeatherSnapshot = {
  venue_name: string | null;
  location_name: string | null;
  temperature_f: number | null;
  wind_mph: number | null;
  wind_gust_mph: number | null;
  precipitation_probability: number | null;
  summary: string;
};

export type PredictionResponse = {
  predicted_winner: string;
  home_win_probability: number;
  away_win_probability: number;
  confidence: "low" | "medium" | "high";
  score: number;
  factors: Record<string, number>;
  ensemble: ModelPrediction[];
  calibrated_home_win_probability: number;
  feature_importance: FeatureImportance[];
  model_notes: string[];
  summary: string;
};

export type DataSourceStatus = {
  name: string;
  enabled: boolean;
  detail: string;
};

export type TeamSnapshot = TeamInput & {
  id: string | null;
  abbreviation: string | null;
  source: string;
};

export type GameSnapshot = {
  id: string;
  sport: Sport;
  date: string;
  name: string;
  home_team: TeamSnapshot;
  away_team: TeamSnapshot;
  neutral_site: boolean;
  home_travel_miles: number;
  away_travel_miles: number;
  venue_name: string | null;
  venue_city: string | null;
  venue_state: string | null;
  weather: WeatherSnapshot | null;
  sources: DataSourceStatus[];
};

export type LivePredictionResponse = PredictionResponse & {
  game: GameSnapshot;
};

export type SavedPrediction = {
  id: number;
  created_at: string;
  game_id: string;
  sport: Sport;
  game_date: string;
  game_name: string;
  predicted_winner: string;
  home_team: string;
  away_team: string;
  home_win_probability: number;
  away_win_probability: number;
  confidence: "low" | "medium" | "high";
  score: number;
  actual_winner: string | null;
  correct: boolean | null;
  resolved_at: string | null;
};

export type PredictionSummary = {
  total: number;
  resolved: number;
  correct: number;
  accuracy: number | null;
  pending: number;
};

export type RecommendedPick = {
  game_id: string;
  sport: Sport;
  game_date: string;
  game_name: string;
  predicted_winner: string;
  probability: number;
  confidence: "low" | "medium" | "high";
  home_team: string;
  away_team: string;
};

export type NotificationPreferences = {
  daily_email: boolean;
  push_alerts: boolean;
  close_game_alerts: boolean;
};

export type UserProfile = {
  id: number;
  display_name: string;
  email: string | null;
  created_at: string;
  plan: Plan;
  notification_preferences: NotificationPreferences;
};

export type Favorite = {
  id: number;
  user_id: number;
  sport: Sport;
  team_id: string | null;
  team_name: string | null;
  league_name: string | null;
  created_at: string;
};

export type FavoriteCreate = {
  sport: Sport;
  team_id?: string | null;
  team_name?: string | null;
  league_name?: string | null;
};

export type DailyFeed = {
  profile: UserProfile | null;
  favorites: Favorite[];
  picks: RecommendedPick[];
};

export type SimulatedTeamSeason = {
  team: string;
  expected_wins: number;
  simulated_wins: number;
  playoff_seed: number;
};

export type SeasonSimulation = {
  sport: Sport;
  simulations: number;
  remaining_games: number;
  teams: SimulatedTeamSeason[];
};

export type LiveTeamScore = {
  id: string;
  name: string;
  abbreviation: string | null;
  home_away: string;
  score: number;
  record: string | null;
};

export type LiveEvent = {
  id: string;
  text: string;
  clock: string | null;
  period: string | null;
  home_score: number;
  away_score: number;
  scoring_play: boolean;
  importance: number;
};

export type LiveWinProbabilityPoint = {
  sequence: number;
  label: string;
  home_win_probability: number;
};

export type LiveMomentumPoint = {
  sequence: number;
  label: string;
  home_momentum: number;
};

export type LivePlayerStat = {
  team: string;
  player: string;
  stat_line: string;
};

export type LiveGameState = {
  game_id: string;
  sport: Sport;
  name: string;
  status: string;
  status_state: string;
  clock: string | null;
  period: string | null;
  home_team: LiveTeamScore;
  away_team: LiveTeamScore;
  home_win_probability: number;
  predicted_winner: string;
  win_probability: LiveWinProbabilityPoint[];
  momentum: LiveMomentumPoint[];
  timeline: LiveEvent[];
  team_stats: Record<string, Record<string, string>>;
  player_stats: LivePlayerStat[];
  expected_updates: string[];
  last_updated: string;
};

export type PublicProfile = {
  id: number;
  display_name: string;
  created_at: string;
  followers: number;
  following: number;
  total_predictions: number;
  resolved_predictions: number;
  accuracy: number | null;
  badges: string[];
};

export type Follow = {
  id: number;
  follower_id: number;
  following_id: number;
  created_at: string;
};

export type GameComment = {
  id: number;
  user_id: number;
  display_name: string;
  sport: Sport;
  game_id: string;
  body: string;
  created_at: string;
};

export type Contest = {
  id: number;
  name: string;
  sport: Sport;
  starts_at: string | null;
  ends_at: string | null;
  created_at: string;
};

export type ContestEntry = {
  id: number;
  contest_id: number;
  user_id: number;
  display_name: string;
  prediction_id: number;
  predicted_winner: string;
  correct: boolean | null;
  created_at: string;
};

export type LeaderboardEntry = {
  user_id: number;
  display_name: string;
  total_predictions: number;
  resolved_predictions: number;
  correct_predictions: number;
  accuracy: number | null;
  score: number;
  badges: string[];
};

export type WeeklyChallenge = {
  id: string;
  title: string;
  description: string;
  target: number;
  progress: number;
  completed: boolean;
};

export type CommunityDashboard = {
  profiles: PublicProfile[];
  leaderboard: LeaderboardEntry[];
  contests: Contest[];
  challenges: WeeklyChallenge[];
};

export type PremiumFeatureSet = {
  plan: Plan;
  unlimited_analysis: boolean;
  premium_models: boolean;
  downloadable_data: boolean;
  value_analysis: boolean;
  ad_free: boolean;
};

export type ModelPerformanceReport = {
  total_predictions: number;
  resolved_predictions: number;
  accuracy: number | null;
  high_confidence_accuracy: number | null;
  average_confidence: number | null;
};

export type BettingValuePick = {
  game_id: string;
  sport: Sport;
  game_name: string;
  predicted_winner: string;
  model_probability: number;
  implied_probability: number | null;
  edge: number | null;
  moneyline: number | null;
  note: string;
};

export type PremiumAnalysis = {
  game_id: string;
  sport: Sport;
  headline: string;
  model_edge_summary: string;
  risk_factors: string[];
  suggested_watch_points: string[];
  value_pick: BettingValuePick | null;
  disclaimer: string;
};
