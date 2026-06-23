import "server-only";
import { cookies } from "next/headers";
import {
  ACCESS_TOKEN_EXPIRY_SAFETY_WINDOW_MS,
  SESSION_COOKIE_NAME,
} from "./constants";
import { readJwtExpiry } from "./jwt";
import { decryptSession, encryptSession, type SessionPayload } from "./session";

const FALLBACK_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 7; // 7 days

/**
 * Pure read of the current session cookie. Safe to call from Server
 * Components — never refreshes, never writes. See lib/auth/actions.ts for
 * the only place that's allowed to refresh and re-set this cookie.
 */
export async function getSession(): Promise<SessionPayload | null> {
  const store = await cookies();
  const raw = store.get(SESSION_COOKIE_NAME)?.value;
  if (!raw) {
    return null;
  }
  return decryptSession(raw);
}

/**
 * True once the access token is within the safety window of its real
 * expiry (or already past it) — callers should treat this the same as
 * "expired" and route through the refresh flow rather than calling FastAPI
 * with a token likely to be rejected mid-request.
 */
export function isAccessTokenExpired(session: SessionPayload): boolean {
  return Date.now() >= session.accessTokenExpiresAt * 1000 - ACCESS_TOKEN_EXPIRY_SAFETY_WINDOW_MS;
}

/**
 * Writes the encrypted session cookie. Only callable from a Route Handler
 * or Server Action (Next.js itself enforces this — calling it during a
 * Server Component render throws).
 */
export async function setSession(payload: SessionPayload): Promise<void> {
  const store = await cookies();
  const refreshExpiry = readJwtExpiry(payload.refreshToken);
  const maxAge = refreshExpiry
    ? Math.max(refreshExpiry - Math.floor(Date.now() / 1000), 0)
    : FALLBACK_COOKIE_MAX_AGE_SECONDS;

  store.set(SESSION_COOKIE_NAME, encryptSession(payload), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge,
  });
}

/** Clears the session cookie. Only callable from a Route Handler or Server Action. */
export async function clearSession(): Promise<void> {
  const store = await cookies();
  store.delete(SESSION_COOKIE_NAME);
}
