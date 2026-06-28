import "server-only";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * This app's own public origin, used only to validate Origin/Referer on
 * state-changing Route Handlers (login, logout, and future mutations).
 * Not a CORS setting — it never reaches the backend, and is unrelated to
 * Next.js's own (unconfigured, default) Server Action origin protection.
 */
function getConfiguredAppOrigin(): string {
  const origin = process.env.APP_ORIGIN;
  if (!origin || origin.trim().length === 0) {
    throw new Error(
      "APP_ORIGIN is not set. Set it to this app's own origin (e.g. http://localhost:3000) " +
        "so state-changing routes can reject cross-origin requests.",
    );
  }
  return origin.replace(/\/+$/, "");
}

function normalizeOrigin(value: string): string {
  const trimmed = value.trim().replace(/\/+$/, "");
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return trimmed;
  }
  return `https://${trimmed}`;
}

function getAllowedOrigins(request: Request): Set<string> {
  void request;
  const allowed = new Set([getConfiguredAppOrigin()]);

  for (const alias of (process.env.APP_ORIGIN_ALIASES ?? "").split(",")) {
    if (alias.trim()) {
      allowed.add(normalizeOrigin(alias));
    }
  }

  if (process.env.RAILWAY_PUBLIC_DOMAIN?.trim()) {
    allowed.add(normalizeOrigin(process.env.RAILWAY_PUBLIC_DOMAIN));
  }

  return allowed;
}

/**
 * True only when the request's Origin (or, if absent, Referer) matches
 * this app's configured origin. A state-changing request with neither
 * header present is treated as a rejection, not a silent pass — per OWASP
 * CSRF guidance, falling back to Referer when Origin is missing, and
 * failing closed when both are missing.
 */
export function isSameOriginRequest(request: Request): boolean {
  const allowedOrigins = getAllowedOrigins(request);
  const origin = request.headers.get("origin");

  if (origin) {
    return allowedOrigins.has(origin);
  }

  const referer = request.headers.get("referer");
  if (referer) {
    try {
      return allowedOrigins.has(new URL(referer).origin);
    } catch {
      return false;
    }
  }

  return false;
}

/**
 * Wraps a state-changing Route Handler (POST/PATCH/DELETE) with the
 * Origin/Referer check above. GET/HEAD handlers must never be wrapped with
 * this — they must never mutate state in the first place (see the refresh
 * flow's use of a Server Action instead of a GET handler, for exactly this
 * reason).
 *
 * Generic over any extra arguments (e.g. Next's `{ params }` context for a
 * dynamic route segment) so a wrapped handler's signature matches what
 * Next.js actually calls it with.
 */
export function withCsrfProtection<Extra extends unknown[]>(
  handler: (request: NextRequest, ...extra: Extra) => Promise<Response>,
) {
  return async (request: NextRequest, ...extra: Extra): Promise<Response> => {
    if (!isSameOriginRequest(request)) {
      return NextResponse.json(
        {
          error: {
            code: "csrf_origin_mismatch",
            message: "Cross-origin request rejected.",
          },
        },
        { status: 403 },
      );
    }
    return handler(request, ...extra);
  };
}
