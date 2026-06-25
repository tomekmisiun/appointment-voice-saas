import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { _resetSessionSecretCacheForTests, encryptSession } from "@/lib/auth/session";
import { PublicShell } from "@/components/marketing/PublicShell";

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

const SESSION_SECRET = Buffer.from("a".repeat(32)).toString("base64");
const COOKIE_NAME = "avs_session";

beforeEach(() => {
  process.env.SESSION_SECRET = SESSION_SECRET;
  _resetSessionSecretCacheForTests();
  cookieStore.raw.clear();
});

afterEach(() => {
  delete process.env.SESSION_SECRET;
  vi.restoreAllMocks();
});

describe("LoginPage", () => {
  it("redirects to /dashboard when already authenticated with a valid token", async () => {
    cookieStore.raw.set(
      COOKIE_NAME,
      encryptSession({
        accessToken: "valid",
        refreshToken: "valid-refresh",
        accessTokenExpiresAt: Math.floor(Date.now() / 1000) + 1800,
      }),
    );
    const { default: LoginPage } = await import("./page");

    await expect(LoginPage()).rejects.toThrow("REDIRECT:/dashboard");
  });

  it("renders the login form (no redirect) when there is no session", async () => {
    const { default: LoginPage } = await import("./page");

    const result = await LoginPage();
    expect(result.type).toBe(PublicShell);
  });

  it("renders the login form (no redirect) when the session's access token looks expired", async () => {
    cookieStore.raw.set(
      COOKIE_NAME,
      encryptSession({
        accessToken: "stale",
        refreshToken: "stale-refresh",
        accessTokenExpiresAt: Math.floor(Date.now() / 1000) - 100,
      }),
    );
    const { default: LoginPage } = await import("./page");

    const result = await LoginPage();
    expect(result.type).toBe(PublicShell);
  });
});
