import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { loginRequestSchema } from "@/features/auth/schemas";
import { getTrustedClientIpHeaders } from "@/lib/api/client-ip";
import { getTenantSlug } from "@/lib/api/config";
import { ApiError } from "@/lib/api/errors";
import { postToBackendUnauthenticated } from "@/lib/api/server";
import type { Token } from "@/lib/api/types";
import { withCsrfProtection } from "@/lib/auth/csrf";
import { readJwtExpiry } from "@/lib/auth/jwt";
import { getLoginTenantSlug, setLoginTenantSlug, setSession } from "@/lib/auth/server";

/**
 * Client Components call this — never FastAPI directly. On success, the
 * tokens are stored only in the encrypted session cookie (see
 * lib/auth/server.ts); the response body never contains them.
 */
export const POST = withCsrfProtection(async (request: NextRequest) => {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: { code: "invalid_request", message: "Request body must be valid JSON." } },
      { status: 400 },
    );
  }

  const parsed = loginRequestSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      {
        error: {
          code: "validation_error",
          message: "Enter a valid email and password.",
          details: parsed.error.issues,
        },
      },
      { status: 422 },
    );
  }

  try {
    const tenantSlug =
      (parsed.data.workspace || undefined) ?? (await getLoginTenantSlug()) ?? getTenantSlug();
    const clientIpHeaders = getTrustedClientIpHeaders(request);
    const token = await postToBackendUnauthenticated<Token>(
      "/api/v1/auth/login",
      { email: parsed.data.email, password: parsed.data.password },
      {
        ...clientIpHeaders,
        ...(tenantSlug ? { "X-Tenant-Slug": tenantSlug } : {}),
      },
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
    if (tenantSlug) {
      await setLoginTenantSlug(tenantSlug);
    }

    return NextResponse.json({ ok: true });
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json(
        { error: { code: error.code ?? "login_failed", message: error.message } },
        { status: error.status },
      );
    }
    throw error;
  }
});
