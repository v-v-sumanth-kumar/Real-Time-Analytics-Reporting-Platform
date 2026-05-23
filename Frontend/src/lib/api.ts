const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type ApiResponse<T> = {
  success: boolean;
  data: T;
  meta?: Record<string, unknown>;
  correlation_id?: string;
  error?: { message: string; code: string };
};

let accessToken: string | null = null;
let organizationId: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
  if (typeof window !== "undefined") {
    if (token) sessionStorage.setItem("access_token", token);
    else sessionStorage.removeItem("access_token");
  }
}

export function getAccessToken(): string | null {
  if (accessToken) return accessToken;
  if (typeof window !== "undefined") {
    return sessionStorage.getItem("access_token");
  }
  return null;
}

export function setOrganizationId(orgId: string | null) {
  organizationId = orgId;
  if (typeof window !== "undefined") {
    if (orgId) localStorage.setItem("organization_id", orgId);
    else localStorage.removeItem("organization_id");
  }
}

export function getOrganizationId(): string | null {
  if (organizationId) return organizationId;
  if (typeof window !== "undefined") {
    return localStorage.getItem("organization_id");
  }
  return null;
}

export function clearAuthSession() {
  setAccessToken(null);
  setOrganizationId(null);
  if (typeof window !== "undefined") {
    sessionStorage.clear();
  }
}

function redirectToLogin() {
  if (typeof window === "undefined") return;
  if (!window.location.pathname.startsWith("/login") && !window.location.pathname.startsWith("/signup")) {
    window.location.href = "/login";
  }
}

async function refreshAccessToken(): Promise<string | null> {
  const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) return null;
  const json: ApiResponse<{ access_token: string; organization?: { id: string } }> =
    await res.json();
  if (json.success && json.data.access_token) {
    setAccessToken(json.data.access_token);
    if (json.data.organization?.id) setOrganizationId(json.data.organization.id);
    return json.data.access_token;
  }
  return null;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const token = getAccessToken();
  const orgId = getOrganizationId();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (orgId) headers["X-Organization-ID"] = orgId;

  let res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (res.status === 401 && token) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers["Authorization"] = `Bearer ${newToken}`;
      res = await fetch(`${API_URL}${path}`, {
        ...options,
        headers,
        credentials: "include",
      });
    }
  }

  if (res.status === 401) {
    clearAuthSession();
    redirectToLogin();
  }

  return res.json();
}
