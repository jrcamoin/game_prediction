export type Sport = "football" | "basketball" | "baseball" | "hockey" | "soccer";

export type TeamInput = {
  name: string;
  rating: number;
  recent_wins: number;
  recent_losses: number;
  injuries: number;
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
};

export type PredictionResponse = {
  predicted_winner: string;
  home_win_probability: number;
  away_win_probability: number;
  confidence: "low" | "medium" | "high";
  score: number;
  factors: Record<string, number>;
  summary: string;
};
