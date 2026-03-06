/**
 * Centralized API configuration for UKIP frontend.
 * Set NEXT_PUBLIC_API_URL in .env.local for non-localhost environments.
 */
export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Authenticated fetch wrapper.
 * - Reads the Bearer token from localStorage (key: "ukip_token") and attaches it.
 * - On HTTP 401, clears the stored token and redirects to /login.
 */
export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = typeof window !== "undefined" ? localStorage.getItem("ukip_token") : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (response.status === 401 && typeof window !== "undefined") {
    localStorage.removeItem("ukip_token");
    // Avoid redirect loop if already on /login
    if (!window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
  }

  return response;
}
