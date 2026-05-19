const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE ?? "ws://localhost:8000";

function authHeader(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const tok = window.localStorage.getItem("aim_token");
  return tok ? { Authorization: `Bearer ${tok}` } : {};
}

export class ApiError extends Error {
  readonly status: number;
  readonly kind: "auth" | "network" | "server" | "client";
  constructor(message: string, status: number, kind: ApiError["kind"]) {
    super(message);
    this.status = status;
    this.kind = kind;
  }
}

export async function api<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...authHeader(),
        ...(init.headers ?? {}),
      },
    });
  } catch (e) {
    // Aborts surface as `AbortError` — let the caller distinguish those
    // from genuine network failures.
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError(
      `Network error: ${(e as Error).message}`,
      0,
      "network",
    );
  }

  if (res.status === 401) {
    // Drop the stale token so the next page load goes back to /login.
    if (typeof window !== "undefined") {
      window.localStorage.removeItem("aim_token");
    }
    throw new ApiError("Sessiya tugadi — qaytadan kiring", 401, "auth");
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    const kind = res.status >= 500 ? "server" : "client";
    throw new ApiError(body || res.statusText, res.status, kind);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function openActivityWS(): WebSocket {
  return new WebSocket(`${WS_BASE}/ws/activity`);
}

export interface UploadedAttachment {
  attachment_id: string;
  filename: string;
  bytes_size: number;
  char_count: number;
  preview: string;
}

// Upload a single chat attachment (multipart). Returns the metadata the
// chat panel needs to render the pill + pass back on /api/chat.
export async function uploadAttachment(file: File): Promise<UploadedAttachment> {
  const fd = new FormData();
  fd.append("file", file);

  let res: Response;
  try {
    res = await fetch(`${BASE}/api/chat/attachments`, {
      method: "POST",
      headers: { ...authHeader() }, // no Content-Type — browser sets the boundary
      body: fd,
    });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError(
      `Network error: ${(e as Error).message}`,
      0,
      "network",
    );
  }
  if (res.status === 401) {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem("aim_token");
    }
    throw new ApiError("Sessiya tugadi — qaytadan kiring", 401, "auth");
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    const kind = res.status >= 500 ? "server" : "client";
    throw new ApiError(body || res.statusText, res.status, kind);
  }
  return (await res.json()) as UploadedAttachment;
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
  if (typeof window !== "undefined") {
    window.localStorage.removeItem("aim_token");
    window.localStorage.removeItem("aim_user");
  }
}

export function hasToken(): boolean {
  return (
    typeof window !== "undefined" &&
    window.localStorage.getItem("aim_token") != null
  );
}

export function getCachedUser(): Me | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem("aim_user");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Me;
  } catch {
    return null;
  }
}
