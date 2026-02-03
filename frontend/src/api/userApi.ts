interface UserChatRequest {
  content: string;
  user_id: string | null;
}

export interface UserChatResponse {
  text: string;
  user_id: string;
}

export async function sendChatMessage(
  request: UserChatRequest,
): Promise<UserChatResponse> {
  const baseUrl = (import.meta.env.VITE_API_URL as string) || "http://localhost:8000";

  const response = await fetch(`${baseUrl}/chat/chat/messages`, {
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
