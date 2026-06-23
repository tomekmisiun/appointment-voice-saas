import "server-only";
import { getBackendApiUrl } from "./config";
import { ApiError, parseErrorBody } from "./errors";

/**
 * Read-only fetch helper for talking to FastAPI directly, server-side.
 *
 * Used by Server Components while the caller's access token is still
 * valid. Deliberately does NOT refresh-on-401 — per this branch's
 * auth design, a Server Component that gets a 401 (or already knows its
 * token looks expired) must redirect through the dedicated refresh flow
 * instead of mutating the session cookie mid-render. Route Handlers and
 * Server Actions, which are allowed to refresh, use their own logic
 * (see lib/auth/actions.ts) rather than this helper's 401 path.
 *
 * Always passes `cache: "no-store"`: this is user-specific, tenant-scoped
 * data — Next.js's fetch caching/memoization must never serve one user's
 * (or one business's) response to a different request.
 */
export async function fetchFromBackend<T>(
  path: string,
  accessToken: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${getBackendApiUrl()}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      ...init?.headers,
      Authorization: `Bearer ${accessToken}`,
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    const body = await parseErrorBody(response);
    throw new ApiError(response.status, body);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

/**
 * Unauthenticated POST helper — used only for login (no token yet) and the
 * refresh call itself (authenticated by the refresh token in the body, not
 * a bearer header). Everything else should use fetchFromBackend.
 */
export async function postToBackendUnauthenticated<T>(
  path: string,
  body: unknown,
  headers?: Record<string, string>,
): Promise<T> {
  const response = await fetch(`${getBackendApiUrl()}${path}`, {
    method: "POST",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...headers,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorBody = await parseErrorBody(response);
    throw new ApiError(response.status, errorBody);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
