"use server";

import { redirect } from "next/navigation";
import { postToBackendUnauthenticated } from "@/lib/api/server";
import type { Token } from "@/lib/api/types";
import { DEFAULT_REFRESH_REDIRECT_TARGET, isSafeInternalPath } from "./constants";
import { readJwtExpiry } from "./jwt";
import { singleFlightRefresh } from "./refresh-lock";
import { clearSession, getSession, setSession } from "./server";

/**
 * The only place in this app allowed to refresh tokens and rewrite the
 * session cookie outside a plain Route Handler — see the refresh flow
 * documented in the plan: a Server Component detects an expired/failed
 * access token and redirects to /auth/refresh?next=..., which renders a
 * Client Component that calls this action on mount.
 *
 * Never redirects back to /auth/refresh itself (only to a validated
 * internal `next` target on success, or /login on genuine failure) — so
 * there is no path that can loop.
 */
export async function refreshSessionAction(requestedNext: string): Promise<void> {
  // Re-validated independently of the page that passed it in — never trust
  // the caller, even though the page already checked this once.
  const next = isSafeInternalPath(requestedNext) ? requestedNext : DEFAULT_REFRESH_REDIRECT_TARGET;

  const session = await getSession();
  if (!session) {
    await clearSession();
    redirect("/login");
  }

  const startingRefreshToken = session.refreshToken;

  try {
    const token = await singleFlightRefresh(startingRefreshToken, () =>
      postToBackendUnauthenticated<Token>("/api/v1/auth/refresh", {
        refresh_token: startingRefreshToken,
      }),
    );

    const accessTokenExpiresAt = readJwtExpiry(token.access_token);
    if (accessTokenExpiresAt === null) {
      throw new Error("Backend issued an access token without a readable exp claim.");
    }

    await setSession({
      accessToken: token.access_token,
      refreshToken: token.refresh_token,
      accessTokenExpiresAt,
    });
  } catch {
    // The backend rotates refresh tokens and enforces single use
    // atomically (Redis SETNX): once *this* call's network request has
    // failed, the starting token is genuinely dead from this action's
    // point of view. There is deliberately no "maybe a concurrent
    // request already won, let me check the cookie again" fallback here
    // — Next.js's cookies() in a Server Action reflects only the cookie
    // this specific request arrived with; it cannot observe a sibling
    // request's Set-Cookie, so re-reading it here would never see a
    // concurrent winner's update and would just be misleading dead code.
    //
    // The actual protection against a same-token race (duplicate effect
    // invocation under Strict Mode, two tabs hitting the same server
    // process) is singleFlightRefresh above: both callers share the one
    // in-flight network call and either both succeed together or both
    // land in this catch block together — there's no "lost the race"
    // case left to detect by the time we get here. A genuinely separate
    // server process (horizontal scaling) is NOT covered by that map and
    // is a known, undefended gap — see refresh-lock.ts's doc comment.
    await clearSession();
    redirect("/login");
  }

  redirect(next);
}
