import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../tests/mocks/server";
import { _resetSessionSecretCacheForTests, decryptSession, encryptSession } from "./session";

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

vi.mock("next/navigation", () => ({
  redirect: vi.fn((path: string) => {
    throw new Error(`REDIRECT:${path}`);
  }),
}));

const BACKEND_URL = "http://backend.test";
const SESSION_SECRET = Buffer.from("a".repeat(32)).toString("base64");
const COOKIE_NAME = "avs_session";

beforeEach(() => {
  process.env.BACKEND_API_URL = BACKEND_URL;
  process.env.SESSION_SECRET = SESSION_SECRET;
  _resetSessionSecretCacheForTests();
  cookieStore.raw.clear();
});

afterEach(() => {
  delete process.env.BACKEND_API_URL;
  delete process.env.SESSION_SECRET;
  vi.restoreAllMocks();
});

function fakeJwt(exp: number): string {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ sub: "1", tenant_id: 1, exp, type: "access" })).toString(
    "base64url",
  );
  return `${header}.${payload}.fake-signature`;
}

function seedSession(refreshToken: string, accessTokenExpiresAt = Math.floor(Date.now() / 1000) - 100) {
  cookieStore.raw.set(
    COOKIE_NAME,
    encryptSession({ accessToken: "expired-access-token", refreshToken, accessTokenExpiresAt }),
  );
}

describe("refreshSessionAction", () => {
  it("on success, stores the new token pair and redirects to the requested safe path", async () => {
    seedSession("old-refresh-token");
    const exp = Math.floor(Date.now() / 1000) + 1800;
    server.use(
      http.post(`${BACKEND_URL}/api/v1/auth/refresh`, async ({ request }) => {
        const body = (await request.json()) as { refresh_token: string };
        expect(body.refresh_token).toBe("old-refresh-token");
        return HttpResponse.json({
          access_token: fakeJwt(exp),
          refresh_token: fakeJwt(exp + 60 * 60 * 24 * 7),
          token_type: "bearer",
        });
      }),
    );

    const { refreshSessionAction } = await import("./actions");

    await expect(refreshSessionAction("/dashboard")).rejects.toThrow("REDIRECT:/dashboard");

    const updated = decryptSession(cookieStore.raw.get(COOKIE_NAME) as string);
    expect(updated?.refreshToken).not.toBe("old-refresh-token");
  });

  it("falls back to the default target when an unsafe next path is requested", async () => {
    seedSession("old-refresh-token");
    const exp = Math.floor(Date.now() / 1000) + 1800;
    server.use(
      http.post(`${BACKEND_URL}/api/v1/auth/refresh`, () =>
        HttpResponse.json({
          access_token: fakeJwt(exp),
          refresh_token: fakeJwt(exp + 60 * 60 * 24 * 7),
          token_type: "bearer",
        }),
      ),
    );

    const { refreshSessionAction } = await import("./actions");

    // "/auth/refresh" itself and any attacker-supplied absolute URL must
    // never be honored — only the small allow-list in lib/auth/constants.
    await expect(refreshSessionAction("https://evil.example")).rejects.toThrow("REDIRECT:/dashboard");
  });

  it("on a genuinely revoked/expired refresh token, clears the session and redirects to /login (never back to /auth/refresh)", async () => {
    seedSession("dead-refresh-token");
    server.use(
      http.post(`${BACKEND_URL}/api/v1/auth/refresh`, () =>
        HttpResponse.json(
          { error: { code: "unauthorized", message: "Refresh token has been revoked" } },
          { status: 401 },
        ),
      ),
    );

    const { refreshSessionAction } = await import("./actions");

    await expect(refreshSessionAction("/dashboard")).rejects.toThrow("REDIRECT:/login");
    expect(cookieStore.raw.has(COOKIE_NAME)).toBe(false);
  });

  it("two concurrent calls sharing the same starting token (same process) share one backend call and both land on the same valid session", async () => {
    // This is the actual protection against the backend's single-use,
    // atomically-rotated refresh token being raced into corrupting the
    // session: singleFlightRefresh ensures both callers await the exact
    // same network call, so there is no "one wins, one loses and clears
    // a session it can't see was already replaced" scenario for same-
    // process concurrency (e.g. a duplicate Strict Mode effect fire, or
    // two tabs hitting the same dev server). A separate cookie re-check
    // cannot substitute for this — see the comment in actions.ts.
    seedSession("raced-refresh-token");
    const winnerExp = Math.floor(Date.now() / 1000) + 1800;
    let backendCallCount = 0;

    server.use(
      http.post(`${BACKEND_URL}/api/v1/auth/refresh`, async ({ request }) => {
        backendCallCount += 1;
        const body = (await request.json()) as { refresh_token: string };
        expect(body.refresh_token).toBe("raced-refresh-token");
        return HttpResponse.json({
          access_token: fakeJwt(winnerExp),
          refresh_token: "rotated-refresh-token",
          token_type: "bearer",
        });
      }),
    );

    const { refreshSessionAction } = await import("./actions");

    const results = await Promise.allSettled([
      refreshSessionAction("/dashboard"),
      refreshSessionAction("/dashboard"),
    ]);

    expect(backendCallCount).toBe(1);
    for (const result of results) {
      expect(result.status).toBe("rejected");
      if (result.status === "rejected") {
        expect(result.reason.message).toBe("REDIRECT:/dashboard");
      }
    }

    const current = decryptSession(cookieStore.raw.get(COOKIE_NAME) as string);
    expect(current?.refreshToken).toBe("rotated-refresh-token");
  });

  it("with no session cookie at all, clears nothing destructively and redirects to /login", async () => {
    const { refreshSessionAction } = await import("./actions");

    await expect(refreshSessionAction("/dashboard")).rejects.toThrow("REDIRECT:/login");
    expect(cookieStore.raw.has(COOKIE_NAME)).toBe(false);
  });
});
