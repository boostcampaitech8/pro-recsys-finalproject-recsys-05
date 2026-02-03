const USER_ID_KEY = "user_id";

export function getUserId(): string | null {
  const userId = localStorage.getItem(USER_ID_KEY);
  return userId || null;
}

export function setUserId(userId: string): void {
  localStorage.setItem(USER_ID_KEY, userId);
}

export function clearUserId(): void {
  localStorage.removeItem(USER_ID_KEY);
}
