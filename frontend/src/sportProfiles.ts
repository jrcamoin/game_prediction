import type { Sport } from "./types";

export const sportProfiles: Record<Sport, { label: string; metric: string; data: string; model: string }> = {
  football: {
    label: "Football",
    metric: "Elo, rest, injury, travel, market",
    data: "ESPN schedules/results with optional odds and weather",
    model: "Rating/form, market, availability, stacked tree",
  },
  basketball: {
    label: "Basketball",
    metric: "Elo, form, rest, lineup, market",
    data: "ESPN schedules/results with optional odds",
    model: "Possession-light baseline with market adjustment",
  },
  baseball: {
    label: "Baseball",
    metric: "Elo, rest, travel, weather, market",
    data: "ESPN schedules/results with optional odds and weather",
    model: "Lower home-field weighting and weather context",
  },
  hockey: {
    label: "Hockey",
    metric: "Elo, form, rest, goalie/lineup proxy, market",
    data: "ESPN schedules/results with optional odds",
    model: "Low-scoring sport calibration with market blend",
  },
  soccer: {
    label: "Soccer",
    metric: "Elo, xG, rest, lineup, travel, market",
    data: "ESPN MLS schedules plus optional StatsBomb xG",
    model: "Expected-goal edge plus stacked tree context",
  },
  golf: {
    label: "Golf",
    metric: "Rating, form, travel, expected output, odds",
    data: "File-backed matchups with sample fallback",
    model: "Neutral-site player matchup scaffold",
  },
  ufc: {
    label: "UFC",
    metric: "Rating, recent form, injury flag, expected output, odds",
    data: "File-backed fight cards with sample fallback",
    model: "Neutral-site fighter matchup scaffold",
  },
};
