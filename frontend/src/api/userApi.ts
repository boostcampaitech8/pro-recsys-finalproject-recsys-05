import type { RecommendedGame } from "./gameApi";

interface UserChatRequest {
  content: string;
  user_id: string | null;
  steam_id?: string | null;
}

export interface UserChatResponse {
  text: string;
  user_id: string;
  games: RecommendedGame[];
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export async function sendChatMessage(
  request: UserChatRequest,
): Promise<UserChatResponse> {
  const response = await fetch(`${API_BASE}/chat/chat/messages`, {
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

  return response.json() as Promise<UserChatResponse>;
}
