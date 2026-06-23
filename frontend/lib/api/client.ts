import { ApiError, parseErrorBody } from "./errors";

/**
 * Client-side fetch helper. Always calls one of *this app's own*
 * `/api/...` Route Handlers, same-origin — never FastAPI directly. The
 * browser never holds a bearer token; the HttpOnly session cookie rides
 * along automatically on these same-origin requests.
 *
 * On a 401, redirects through the exact same /auth/refresh flow Server
 * Components use, instead of refreshing here — Client Components stay out
 * of the token lifecycle entirely, by design (see lib/auth/actions.ts).
 */
export async function clientFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);

  if (response.status === 401) {
    const next = window.location.pathname.startsWith("/dashboard/bookings")
      ? "/dashboard/bookings"
      : "/dashboard";
    window.location.assign(`/auth/refresh?next=${encodeURIComponent(next)}`);
    // Throw rather than resolve: the page is navigating away, so callers
    // (React Query) should treat this as pending, not render an error
    // flash for the instant before the redirect takes effect.
    throw new Error("Session expired — redirecting to sign in again.");
  }

  if (!response.ok) {
    const body = await parseErrorBody(response);
    throw new ApiError(response.status, body);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
