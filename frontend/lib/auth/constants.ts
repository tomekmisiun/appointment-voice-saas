export const SESSION_COOKIE_NAME = "avs_session";
export const LOGIN_TENANT_COOKIE_NAME = "avs_login_tenant";

/**
 * Treat an access token as expired this many ms before its literal `exp`,
 * so a request that starts just before expiry doesn't complete just after
 * it, and to absorb small clock skew between this server and the token
 * issuer. Applied everywhere expiry is checked (see isAccessTokenExpired).
 */
export const ACCESS_TOKEN_EXPIRY_SAFETY_WINDOW_MS = 30_000;

/**
 * Internal navigation targets the refresh flow is allowed to redirect back
 * to. Deliberately excludes "/auth/refresh" and "/login" themselves, so a
 * misused or tampered `next` value can never produce a redirect loop.
 */
export const SAFE_REFRESH_REDIRECT_TARGETS = ["/dashboard", "/dashboard/bookings", "/dashboard/staff"] as const;
export const DEFAULT_REFRESH_REDIRECT_TARGET = "/dashboard";

export function isSafeInternalPath(path: string): boolean {
  return (SAFE_REFRESH_REDIRECT_TARGETS as readonly string[]).includes(path);
}
