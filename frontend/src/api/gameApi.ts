interface RecommendationRequest {
  steamid: string;
  top_k?: number;
}

export interface RecommendedGame {
  app_id: number;
  name: string | null;
  score: number | null;
  header_image: string | null;
  short_description_kr: string | null;
  genres_kr: string[] | null;
  price: number | null;
  release_date: string | null;
}

interface RecommendationResponse {
  steamid: string;
  is_playtime_public: boolean;
  played_games_count: number;
  recommended_games: RecommendedGame[];
  model_type: string;
  top_k: number;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export async function getGameRecommendations(
  request: RecommendationRequest,
): Promise<RecommendationResponse> {
  const response = await fetch(`${API_BASE}/rec/recommend-from-steam`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    let errorMessage = `API Error: ${response.statusText}`;
    try {
      const error = (await response.json()) as { detail?: string };
      errorMessage = error.detail || errorMessage;
    } catch {
      // JSON 파싱 실패 시 무시하고 기본 메시지 사용
    }
    throw new Error(errorMessage);
  }

  return response.json() as Promise<RecommendationResponse>;
}
