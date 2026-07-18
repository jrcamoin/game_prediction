import type {
  CommunityDashboard,
  BettingValuePick,
  Contest,
  ContestEntry,
  GameSnapshot,
  GameComment,
  LivePredictionResponse,
  DailyFeed,
  Favorite,
  FavoriteCreate,
  LiveGameState,
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
  UserProfile,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type ApiValidationError = {
  msg: string;
};

export async function predictGame(payload: PredictionRequest): Promise<PredictionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/predict`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const message = await readErrorMessage(response);
    throw new Error(message);
  }

  return response.json();
}

export async function fetchUpcomingGames(sport: Sport): Promise<GameSnapshot[]> {
  const response = await fetch(`${API_BASE_URL}/api/games/upcoming?sport=${sport}&days=30`);
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchModelStatus(): Promise<ModelStatus> {
  const response = await fetch(`${API_BASE_URL}/api/model/status`);
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchRecommendedPicks(sport: Sport): Promise<RecommendedPick[]> {
  const response = await fetch(`${API_BASE_URL}/api/games/recommendations?sport=${sport}&days=30&limit=5`);
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function predictLiveGame(sport: Sport, gameId: string): Promise<LivePredictionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/predict/live/${sport}/${gameId}`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchPredictionHistory(query = "", sport: Sport | "all" = "all"): Promise<SavedPrediction[]> {
  const params = new URLSearchParams({ limit: "25" });
  if (query.trim()) {
    params.set("query", query.trim());
  }
  if (sport !== "all") {
    params.set("sport", sport);
  }
  const response = await fetch(`${API_BASE_URL}/api/predictions?${params.toString()}`);
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchPredictionSummary(): Promise<PredictionSummary> {
  const response = await fetch(`${API_BASE_URL}/api/predictions/summary`);
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function gradePredictionHistory(): Promise<SavedPrediction[]> {
  const response = await fetch(`${API_BASE_URL}/api/predictions/grade`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchUsers(): Promise<UserProfile[]> {
  const response = await fetch(`${API_BASE_URL}/api/users`);
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function createUserProfile(displayName: string, email: string): Promise<UserProfile> {
  const response = await fetch(`${API_BASE_URL}/api/users`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ display_name: displayName, email: email || null }),
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function updateNotificationPreferences(
  userId: number,
  preferences: NotificationPreferences,
): Promise<UserProfile> {
  const response = await fetch(`${API_BASE_URL}/api/users/${userId}/notifications`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(preferences),
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchFavorites(userId: number): Promise<Favorite[]> {
  const response = await fetch(`${API_BASE_URL}/api/users/${userId}/favorites`);
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function addFavorite(userId: number, favorite: FavoriteCreate): Promise<Favorite> {
  const response = await fetch(`${API_BASE_URL}/api/users/${userId}/favorites`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(favorite),
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function removeFavorite(userId: number, favoriteId: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/users/${userId}/favorites/${favoriteId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
}

export async function fetchDailyFeed(userId: number): Promise<DailyFeed> {
  const response = await fetch(`${API_BASE_URL}/api/users/${userId}/daily-feed`);
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchSeasonSimulation(sport: Sport): Promise<SeasonSimulation> {
  const response = await fetch(`${API_BASE_URL}/api/simulations/season?sport=${sport}&days=30&simulations=1000`);
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchLiveGameState(sport: Sport, gameId: string): Promise<LiveGameState> {
  const response = await fetch(`${API_BASE_URL}/api/live/${sport}/${gameId}`);
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchCommunityDashboard(userId: number | null): Promise<CommunityDashboard> {
  const suffix = userId ? `?user_id=${userId}` : "";
  const response = await fetch(`${API_BASE_URL}/api/community${suffix}`);
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function followUser(followerId: number, followingId: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/community/follows`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ follower_id: followerId, following_id: followingId }),
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
}

export async function unfollowUser(followerId: number, followingId: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/community/follows/${followerId}/${followingId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
}

export async function fetchGameComments(sport: Sport, gameId: string): Promise<GameComment[]> {
  const response = await fetch(`${API_BASE_URL}/api/community/comments/${sport}/${gameId}`);
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function addGameComment(userId: number, sport: Sport, gameId: string, body: string): Promise<GameComment> {
  const response = await fetch(`${API_BASE_URL}/api/community/comments`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ user_id: userId, sport, game_id: gameId, body }),
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchContests(): Promise<Contest[]> {
  const response = await fetch(`${API_BASE_URL}/api/community/contests`);
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function enterContest(contestId: number, userId: number, predictionId: number): Promise<ContestEntry> {
  const response = await fetch(`${API_BASE_URL}/api/community/contests/${contestId}/entries`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ user_id: userId, prediction_id: predictionId }),
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchPremiumFeatures(userId: number): Promise<PremiumFeatureSet> {
  const response = await fetch(`${API_BASE_URL}/api/premium/features/${userId}`);
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function upgradeToPro(userId: number): Promise<UserProfile> {
  const response = await fetch(`${API_BASE_URL}/api/premium/upgrade/${userId}`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchPremiumPerformance(userId: number): Promise<ModelPerformanceReport> {
  const response = await fetch(`${API_BASE_URL}/api/premium/performance?user_id=${userId}`);
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchPremiumValuePicks(userId: number, sport: Sport): Promise<BettingValuePick[]> {
  const response = await fetch(`${API_BASE_URL}/api/premium/value-picks?user_id=${userId}&sport=${sport}&days=30`);
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export async function fetchPremiumAnalysis(userId: number, sport: Sport, gameId: string): Promise<PremiumAnalysis> {
  const response = await fetch(`${API_BASE_URL}/api/premium/analysis/${sport}/${gameId}?user_id=${userId}`);
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export function premiumCsvUrl(userId: number): string {
  return `${API_BASE_URL}/api/premium/export/predictions.csv?user_id=${userId}`;
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body = await response.clone().json();
    if (Array.isArray(body.detail)) {
      return body.detail.map((item: ApiValidationError) => item.msg).join(" ");
    }
    if (typeof body.detail === "string") {
      return body.detail;
    }
  } catch {
    // Fall back to text below when the API does not return JSON.
  }

  return (await response.text()) || "Prediction request failed";
}
