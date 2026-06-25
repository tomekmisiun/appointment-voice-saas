import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { registerRequestSchema } from "@/features/auth/schemas";
import { getTrustedClientIpHeaders } from "@/lib/api/client-ip";
import { ApiError } from "@/lib/api/errors";
import { postToBackendUnauthenticated } from "@/lib/api/server";
import type { TenantSignupResponse, Token } from "@/lib/api/types";
import { withCsrfProtection } from "@/lib/auth/csrf";
import { readJwtExpiry } from "@/lib/auth/jwt";
import { clearSession, setLoginTenantSlug, setSession } from "@/lib/auth/server";

export const POST = withCsrfProtection(async (request: NextRequest) => {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: { code: "invalid_request", message: "Request body must be valid JSON." } }, { status: 400 });
  }

  const parsed = registerRequestSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: { code: "validation_error", message: "Check the business name, email and password.", details: parsed.error.issues } }, { status: 422 });
  }

  const clientIpHeaders = getTrustedClientIpHeaders(request);
  let signup: TenantSignupResponse;
  try {
    signup = await postToBackendUnauthenticated<TenantSignupResponse>(
      "/api/v1/signup",
      parsed.data,
      clientIpHeaders,
    );
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json({ error: { code: error.code ?? "registration_failed", message: error.message } }, { status: error.status });
    }
    throw error;
  }

  await setLoginTenantSlug(signup.tenant.slug);

  try {
    const token = await postToBackendUnauthenticated<Token>(
      "/api/v1/auth/login",
      { email: parsed.data.admin_email, password: parsed.data.admin_password },
      { ...clientIpHeaders, "X-Tenant-Slug": signup.tenant.slug },
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

    return NextResponse.json({ ok: true, authenticated: true }, { status: 201 });
  } catch {
    // The tenant and owner already exist. Preserve that committed success and
    // let the remembered workspace cookie recover through the normal login.
    await clearSession();
    return NextResponse.json({ ok: true, authenticated: false }, { status: 201 });
  }
});
