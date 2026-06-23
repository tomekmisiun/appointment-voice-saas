import "server-only";

/**
 * Server-only backend base URL. Deliberately not NEXT_PUBLIC_-prefixed:
 * under the BFF design the browser never calls FastAPI directly, so this
 * never needs to reach client bundles or be allowed via CORS.
 */
export function getBackendApiUrl(): string {
  const url = process.env.BACKEND_API_URL;
  if (!url || url.trim().length === 0) {
    throw new Error(
      "BACKEND_API_URL is not set. Copy frontend/.env.example to frontend/.env.local " +
        "and point it at the running FastAPI backend (e.g. http://localhost:8000).",
    );
  }
  return url.replace(/\/+$/, "");
}

/**
 * Which backend tenant this deployment's login should authenticate
 * against. Optional — when unset, the backend falls back to its own
 * DEFAULT_TENANT_SLUG ("default"), matching today's seed/demo setup.
 *
 * Deliberately only used on the pre-auth login call (see
 * app/api/auth/login/route.ts), never on authenticated requests: the
 * backend's tenant-membership check rejects a request whose
 * X-Tenant-Slug doesn't match the JWT's own tenant
 * (app/api/dependencies/auth.py), so sending a configured slug on every
 * authenticated call would turn a misconfiguration into every request
 * failing, instead of just login. Authenticated requests already get
 * their correct tenant from the JWT itself, set at login/refresh time.
 */
export function getTenantSlug(): string | undefined {
  const slug = process.env.TENANT_SLUG;
  return slug && slug.trim().length > 0 ? slug.trim() : undefined;
}
