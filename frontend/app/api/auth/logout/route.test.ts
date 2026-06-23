import { http, HttpResponse } from "msw";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../../../tests/mocks/server";
import { _resetSessionSecretCacheForTests, encryptSession } from "@/lib/auth/session";

const cookieStore = vi.hoisted(() => {
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

function makeRequest(headers: Record<string, string> = {}) {
  return new NextRequest(`${APP_ORIGIN}/api/auth/logout`, {
    method: "POST",
    headers: { origin: APP_ORIGIN, ...headers },
  });
}

describe("POST /api/auth/logout", () => {
  it("rejects a cross-origin request and leaves any existing session untouched", async () => {
    cookieStore.raw.set(
      "avs_session",
      encryptSession({ accessToken: "a", refreshToken: "r", accessTokenExpiresAt: 9999999999 }),
    );
    const { POST } = await import("./route");

    const response = await POST(makeRequest({ origin: "https://evil.example" }));

    expect(response.status).toBe(403);
    expect(cookieStore.raw.has("avs_session")).toBe(true);
  });

  it("clears the session cookie even when there was no session to begin with", async () => {
    const { POST } = await import("./route");

    const response = await POST(makeRequest());
    const json = await response.json();

    expect(response.status).toBe(200);
    expect(json).toEqual({ ok: true });
    expect(cookieStore.raw.has("avs_session")).toBe(false);
  });

  it("revokes the refresh token server-side, then clears the local cookie", async () => {
    let receivedRefreshToken: string | null = null;
    server.use(
      http.post(`${BACKEND_URL}/api/v1/auth/logout`, async ({ request }) => {
        const body = (await request.json()) as { refresh_token: string };
        receivedRefreshToken = body.refresh_token;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    cookieStore.raw.set(
      "avs_session",
      encryptSession({ accessToken: "a", refreshToken: "stored-refresh-token", accessTokenExpiresAt: 9999999999 }),
    );
    const { POST } = await import("./route");

    const response = await POST(makeRequest());

    expect(response.status).toBe(200);
    expect(receivedRefreshToken).toBe("stored-refresh-token");
    expect(cookieStore.raw.has("avs_session")).toBe(false);
  });

  it("still clears the local cookie even if the backend revoke call fails", async () => {
    server.use(
      http.post(`${BACKEND_URL}/api/v1/auth/logout`, () =>
        HttpResponse.json({ error: { code: "unauthorized", message: "already revoked" } }, { status: 401 }),
      ),
    );
    cookieStore.raw.set(
      "avs_session",
      encryptSession({ accessToken: "a", refreshToken: "stale-refresh-token", accessTokenExpiresAt: 9999999999 }),
    );
    const { POST } = await import("./route");

    const response = await POST(makeRequest());
    const json = await response.json();

    expect(response.status).toBe(200);
    expect(json).toEqual({ ok: true });
    expect(cookieStore.raw.has("avs_session")).toBe(false);
  });
});
