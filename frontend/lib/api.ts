const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE ?? "ws://localhost:8000";

function authHeader(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const tok = window.localStorage.getItem("aim_token");
  return tok ? { Authorization: `Bearer ${tok}` } : {};
}

export async function api<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeader(),
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function openActivityWS(): WebSocket {
  return new WebSocket(`${WS_BASE}/ws/activity`);
}

export type Role = "admin" | "analyst" | "viewer";

export interface Me {
  id: string | null;
  username: string;
  role: Role;
}

export async function login(
  username: string,
  password: string,
): Promise<{ access_token: string; user: Me }> {
  return api("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function logout(): void {
  if (typeof window !== "undefined") window.localStorage.removeItem("aim_token");
}
