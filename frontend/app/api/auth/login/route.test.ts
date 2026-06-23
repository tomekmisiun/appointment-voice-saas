import { http, HttpResponse } from "msw";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../../../tests/mocks/server";
import { _resetSessionSecretCacheForTests } from "@/lib/auth/session";

const cookieStore = vi.hoisted(() => {
  // Re-implemented inline (not imported) because vi.mock factories run
  // before module-level imports are available to reference.
  const raw = new Map<string, string>();
  return {
    raw,
    get: (name: string) => (raw.has(name) ? { name, value: raw.get(name) as string } : undefined),
    set: (name: string, value: string) => {
      raw.set(name, value);
    },
    delete: (name: string) => {
      raw.delete(name);
    },
  };
});

vi.mock("next/headers", () => ({
  cookies: async () => cookieStore,
}));

const APP_ORIGIN = "http://localhost:3000";
const BACKEND_URL = "http://backend.test";
const SESSION_SECRET = Buffer.from("a".repeat(32)).toString("base64");

beforeEach(() => {
  process.env.APP_ORIGIN = APP_ORIGIN;
  process.env.BACKEND_API_URL = BACKEND_URL;
  process.env.SESSION_SECRET = SESSION_SECRET;
  _resetSessionSecretCacheForTests();
  cookieStore.raw.clear();
});

afterEach(() => {
  delete process.env.APP_ORIGIN;
  delete process.env.BACKEND_API_URL;
  delete process.env.SESSION_SECRET;
  vi.restoreAllMocks();
});

function makeRequest(body: unknown, headers: Record<string, string> = {}) {
  return new NextRequest(`${APP_ORIGIN}/api/auth/login`, {
    method: "POST",
    headers: { origin: APP_ORIGIN, "content-type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
}

// Real shape minted by app.core.security: header.payload.signature, HS256.
function fakeJwt(exp: number): string {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ sub: "1", tenant_id: 1, exp, type: "access" })).toString(
    "base64url",
  );
  return `${header}.${payload}.fake-signature`;
}

describe("POST /api/auth/login", () => {
  it("rejects a cross-origin request before touching the backend", async () => {
    const { POST } = await import("./route");
    let backendCalled = false;
    server.use(
      http.post(`${BACKEND_URL}/api/v1/auth/login`, () => {
        backendCalled = true;
        return HttpResponse.json({ access_token: "x", refresh_token: "y", token_type: "bearer" });
      }),
    );

    const response = await POST(makeRequest({ email: "a@b.com", password: "secret123" }, { origin: "https://evil.example" }));

    expect(response.status).toBe(403);
    expect(backendCalled).toBe(false);
  });

  it("rejects an invalid email/password shape with 422 before touching the backend", async () => {
    const { POST } = await import("./route");
    let backendCalled = false;
    server.use(
      http.post(`${BACKEND_URL}/api/v1/auth/login`, () => {
        backendCalled = true;
        return HttpResponse.json({ access_token: "x", refresh_token: "y", token_type: "bearer" });
      }),
    );

    const response = await POST(makeRequest({ email: "not-an-email", password: "" }));

    expect(response.status).toBe(422);
    expect(backendCalled).toBe(false);
  });

  it("on valid credentials, sets the session cookie and never echoes tokens to the client", async () => {
    const { POST } = await import("./route");
    const exp = Math.floor(Date.now() / 1000) + 1800;
    server.use(
      http.post(`${BACKEND_URL}/api/v1/auth/login`, () =>
        HttpResponse.json({
          access_token: fakeJwt(exp),
          refresh_token: fakeJwt(exp + 60 * 60 * 24 * 7),
          token_type: "bearer",
        }),
      ),
    );

    const response = await POST(makeRequest({ email: "owner@example.com", password: "secret123" }));
    const json = await response.json();

    expect(response.status).toBe(200);
    expect(json).toEqual({ ok: true });
    expect(JSON.stringify(json)).not.toContain("eyJ"); // no JWT leaks into the body
    expect(cookieStore.raw.has("avs_session")).toBe(true);
  });

  it("propagates the backend's 401 for invalid credentials without setting a session", async () => {
    const { POST } = await import("./route");
    server.use(
      http.post(`${BACKEND_URL}/api/v1/auth/login`, () =>
        HttpResponse.json(
          { error: { code: "unauthorized", message: "Invalid email or password" } },
          { status: 401 },
        ),
      ),
    );

    const response = await POST(makeRequest({ email: "owner@example.com", password: "wrong" }));
    const json = await response.json();

    expect(response.status).toBe(401);
    expect(json.error.code).toBe("unauthorized");
    expect(cookieStore.raw.has("avs_session")).toBe(false);
  });

  it("sends X-Tenant-Slug on the login call when TENANT_SLUG is configured", async () => {
    process.env.TENANT_SLUG = "acme";
    const { POST } = await import("./route");
    let receivedSlug: string | null = null;
    const exp = Math.floor(Date.now() / 1000) + 1800;
    server.use(
      http.post(`${BACKEND_URL}/api/v1/auth/login`, ({ request }) => {
        receivedSlug = request.headers.get("x-tenant-slug");
        return HttpResponse.json({
          access_token: fakeJwt(exp),
          refresh_token: fakeJwt(exp + 60 * 60 * 24 * 7),
          token_type: "bearer",
        });
      }),
    );

    await POST(makeRequest({ email: "owner@example.com", password: "secret123" }));

    expect(receivedSlug).toBe("acme");
    delete process.env.TENANT_SLUG;
  });

  it("omits X-Tenant-Slug entirely when TENANT_SLUG is not configured, preserving the backend's own default", async () => {
    delete process.env.TENANT_SLUG;
    const { POST } = await import("./route");
    let receivedSlug: string | null | undefined;
    const exp = Math.floor(Date.now() / 1000) + 1800;
    server.use(
      http.post(`${BACKEND_URL}/api/v1/auth/login`, ({ request }) => {
        receivedSlug = request.headers.get("x-tenant-slug");
        return HttpResponse.json({
          access_token: fakeJwt(exp),
          refresh_token: fakeJwt(exp + 60 * 60 * 24 * 7),
          token_type: "bearer",
        });
      }),
    );

    await POST(makeRequest({ email: "owner@example.com", password: "secret123" }));

    expect(receivedSlug).toBeNull();
  });
});
