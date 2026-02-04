const USER_ID_KEY = "user_id";
const STEAM_ID_KEY = "steam_id";

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

export function getSteamId(): string | null {
  const steamId = localStorage.getItem(STEAM_ID_KEY);
  return steamId || null;
}

export function setSteamId(steamId: string): void {
  localStorage.setItem(STEAM_ID_KEY, steamId);
}

export function clearSteamId(): void {
  localStorage.removeItem(STEAM_ID_KEY);
}
