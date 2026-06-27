import { NextResponse } from "next/server";
import { ApiError } from "@/lib/api/errors";
import { postToBackendUnauthenticated } from "@/lib/api/server";
import type { Token } from "@/lib/api/types";
import { readJwtExpiry } from "@/lib/auth/jwt";
import { setSession } from "@/lib/auth/server";

/**
 * BFF handler for the public demo session. Calls POST /api/v1/auth/demo on
 * the FastAPI backend (no credentials needed) and stores the returned tokens
 * in the same encrypted session cookie as a normal login. The browser never
 * sees the tokens — they stay server-side only.
 *
 * No CSRF guard: this endpoint does not mutate any user-owned state and is
 * explicitly rate-limited on the backend. The demo session itself is
 * read-only by design (require_non_demo_user blocks all mutations).
 */
export async function POST(): Promise<NextResponse> {
  try {
    const token = await postToBackendUnauthenticated<Token>("/api/v1/auth/demo", {});

    const accessTokenExpiresAt = readJwtExpiry(token.access_token);
    if (accessTokenExpiresAt === null) {
      return NextResponse.json(
        { error: { code: "invalid_token", message: "Backend issued a token without a readable expiry." } },
        { status: 500 },
      );
    }

    await setSession({
      accessToken: token.access_token,
      refreshToken: token.refresh_token,
      accessTokenExpiresAt,
    });

    return NextResponse.json({ ok: true });
  } catch (error) {
    if (error instanceof ApiError) {
      const statusCode = error.status === 503 ? 503 : error.status;
      return NextResponse.json(
        { error: { code: error.code ?? "demo_unavailable", message: error.message } },
        { status: statusCode },
      );
    }
    throw error;
  }
}
