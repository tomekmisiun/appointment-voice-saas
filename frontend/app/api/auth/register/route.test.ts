import { http, HttpResponse } from "msw";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../../../tests/mocks/server";
import { _resetSessionSecretCacheForTests } from "@/lib/auth/session";

const cookieStore = vi.hoisted(() => {
  const raw = new Map<string, string>();
  return {
    raw,
    get: (name: string) => (raw.has(name) ? { name, value: raw.get(name) as string } : undefined),
    set: (name: string, value: string) => raw.set(name, value),
    delete: (name: string) => raw.delete(name),
  };
});

vi.mock("next/headers", () => ({ cookies: async () => cookieStore }));

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
  delete process.env.BFF_TRUST_FORWARDED_HEADERS;
  vi.restoreAllMocks();
});

function makeRequest(body: unknown, origin = APP_ORIGIN, headers: Record<string, string> = {}) {
  return new NextRequest(`${APP_ORIGIN}/api/auth/register`, {
    method: "POST",
    headers: { origin, "content-type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
}

describe("POST /api/auth/register", () => {
  it("rejects cross-origin registration before calling the backend", async () => {
    const { POST } = await import("./route");
    let backendCalled = false;
    server.use(http.post(`${BACKEND_URL}/api/v1/signup`, () => { backendCalled = true; return HttpResponse.json({}); }));

    const response = await POST(makeRequest({ salon_name: "North Studio", admin_email: "owner@example.com", admin_password: "secret123" }, "https://evil.example"));

    expect(response.status).toBe(403);
    expect(backendCalled).toBe(false);
  });

  it("validates registration input before calling the backend", async () => {
    const { POST } = await import("./route");
    const response = await POST(makeRequest({ salon_name: "", admin_email: "bad", admin_password: "short" }));
    expect(response.status).toBe(422);
  });

  it("creates the tenant, logs in against its slug, and stores the session", async () => {
    const { POST } = await import("./route");
    let receivedBody: unknown;
    let receivedLoginSlug: string | null = null;
    const exp = Math.floor(Date.now() / 1000) + 1800;
    server.use(http.post(`${BACKEND_URL}/api/v1/signup`, async ({ request }) => {
      receivedBody = await request.json();
      return HttpResponse.json({ tenant: { id: 4, slug: "north-studio" }, user: { id: 9 } }, { status: 201 });
    }), http.post(`${BACKEND_URL}/api/v1/auth/login`, ({ request }) => {
      receivedLoginSlug = request.headers.get("x-tenant-slug");
      return HttpResponse.json({
        access_token: fakeJwt(exp),
        refresh_token: fakeJwt(exp + 3600),
        token_type: "bearer",
      });
    }));

    const body = { salon_name: "North Studio", admin_email: "owner@example.com", admin_password: "secret123" };
    const response = await POST(makeRequest(body));

    expect(response.status).toBe(201);
    expect(await response.json()).toEqual({ ok: true, authenticated: true });
    expect(receivedBody).toEqual(body);
    expect(receivedLoginSlug).toBe("north-studio");
    expect(cookieStore.raw.has("avs_session")).toBe(true);
    expect(cookieStore.raw.get("avs_login_tenant")).toBe("north-studio");
  });

  it("acknowledges a committed signup and preserves its slug when automatic login fails", async () => {
    const { POST } = await import("./route");
    cookieStore.raw.set("avs_session", "previous-session");
    server.use(
      http.post(`${BACKEND_URL}/api/v1/signup`, () =>
        HttpResponse.json({ tenant: { slug: "north-studio" }, user: {} }, { status: 201 }),
      ),
      http.post(`${BACKEND_URL}/api/v1/auth/login`, () =>
        HttpResponse.json({ error: { code: "rate_limited", message: "Too many requests" } }, { status: 429 }),
      ),
    );

    const body = { salon_name: "North Studio", admin_email: "owner@example.com", admin_password: "secret123" };
    const response = await POST(makeRequest(body));

    expect(response.status).toBe(201);
    expect(await response.json()).toEqual({ ok: true, authenticated: false });
    expect(cookieStore.raw.get("avs_login_tenant")).toBe("north-studio");
    expect(cookieStore.raw.has("avs_session")).toBe(false);
  });

  it("forwards a validated client IP to signup and login only when proxy headers are trusted", async () => {
    process.env.BFF_TRUST_FORWARDED_HEADERS = "true";
    const { POST } = await import("./route");
    const receivedIps: Array<string | null> = [];
    const exp = Math.floor(Date.now() / 1000) + 1800;
    server.use(
      http.post(`${BACKEND_URL}/api/v1/signup`, ({ request }) => {
        receivedIps.push(request.headers.get("x-forwarded-for"));
        return HttpResponse.json({ tenant: { slug: "north-studio" }, user: {} }, { status: 201 });
      }),
      http.post(`${BACKEND_URL}/api/v1/auth/login`, ({ request }) => {
        receivedIps.push(request.headers.get("x-forwarded-for"));
        return HttpResponse.json({ access_token: fakeJwt(exp), refresh_token: fakeJwt(exp + 3600), token_type: "bearer" });
      }),
    );

    const body = { salon_name: "North Studio", admin_email: "owner@example.com", admin_password: "secret123" };
    const response = await POST(makeRequest(body, APP_ORIGIN, { "x-forwarded-for": "198.51.100.20, 10.0.0.1" }));

    expect(response.status).toBe(201);
    expect(receivedIps).toEqual(["198.51.100.20", "198.51.100.20"]);
  });
});

function fakeJwt(exp: number): string {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ sub: "1", tenant_id: 4, exp, type: "access" })).toString("base64url");
  return `${header}.${payload}.fake-signature`;
}
