import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../tests/mocks/server";
import { encryptSession, _resetSessionSecretCacheForTests } from "@/lib/auth/session";

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

// getCurrentBusinessContext is wrapped in React's cache(), which memoizes
// by argument across this whole test file (dynamic import() doesn't reset
// the module registry between tests, and there's no per-request reset
// outside Next.js's own server runtime). Each test must use a distinct
// access token so one test's cached result can never leak into another's.
let tokenCounter = 0;
function seedValidSession(): string {
  tokenCounter += 1;
  const accessToken = `valid-access-token-${tokenCounter}`;
  cookieStore.raw.set(
    COOKIE_NAME,
    encryptSession({
      accessToken,
      refreshToken: `valid-refresh-token-${tokenCounter}`,
      accessTokenExpiresAt: Math.floor(Date.now() / 1000) + 1800,
    }),
  );
  return accessToken;
}

function business(id: number, overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id,
    tenant_id: 1,
    name: `Business ${id}`,
    timezone: "Europe/Warsaw",
    phone: null,
    owner_notification_phone: null,
    transfer_phone_number: null,
    is_active: true,
    transfer_enabled: false,
    transfer_destination_policy: "business_phone",
    booking_mode: "internal_booking",
    external_booking_url: null,
    external_booking_label: null,
    external_booking_provider: null,
    subscription_plan: "full_booking",
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

const ME_RESPONSE = { id: 1, email: "owner@example.com", is_active: true, role: "admin" };

describe("DashboardLayout", () => {
  it("redirects to /login when there is no session", async () => {
    const { default: DashboardLayout } = await import("./layout");

    await expect(DashboardLayout({ children: null })).rejects.toThrow("REDIRECT:/login");
  });

  it("redirects to the refresh flow when the access token looks expired", async () => {
    cookieStore.raw.set(
      COOKIE_NAME,
      encryptSession({
        accessToken: "stale",
        refreshToken: "stale-refresh",
        accessTokenExpiresAt: Math.floor(Date.now() / 1000) - 100,
      }),
    );
    const { default: DashboardLayout } = await import("./layout");

    await expect(DashboardLayout({ children: null })).rejects.toThrow("REDIRECT:/auth/refresh?next=/dashboard");
  });

  it("redirects to the refresh flow when FastAPI rejects an apparently-valid token with 401", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () =>
        HttpResponse.json({ error: { code: "unauthorized", message: "nope" } }, { status: 401 }),
      ),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([])),
    );
    const { default: DashboardLayout } = await import("./layout");

    await expect(DashboardLayout({ children: null })).rejects.toThrow("REDIRECT:/auth/refresh?next=/dashboard");
  });

  it("renders the no-business state when there are zero active businesses", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(ME_RESPONSE)),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([])),
    );
    const { default: DashboardLayout } = await import("./layout");
    const { NoBusinessState } = await import("@/features/dashboard/components/NoBusinessState");

    const result = await DashboardLayout({ children: null });

    expect(result.type).toBe(NoBusinessState);
  });

  it("renders the no-business state when every returned business is inactive", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(ME_RESPONSE)),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () =>
        HttpResponse.json([business(1, { is_active: false })]),
      ),
    );
    const { default: DashboardLayout } = await import("./layout");
    const { NoBusinessState } = await import("@/features/dashboard/components/NoBusinessState");

    const result = await DashboardLayout({ children: null });

    expect(result.type).toBe(NoBusinessState);
  });

  it("renders the app shell with the single active business when there's exactly one", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(ME_RESPONSE)),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
    );
    const { default: DashboardLayout } = await import("./layout");
    const { AppShell } = await import("@/components/layout/AppShell");
    const { QueryProvider } = await import("@/components/providers/QueryProvider");

    const result = await DashboardLayout({ children: "child-content" });

    expect(result.type).toBe(AppShell);
    expect(result.props.business.id).toBe(42);
    expect(result.props.user.email).toBe("owner@example.com");
    // Children are wrapped in QueryProvider (added for the bookings list's
    // client-side data fetching) rather than passed straight through.
    expect(result.props.children.type).toBe(QueryProvider);
    expect(result.props.children.props.children).toBe("child-content");
  });

  it("renders the multiple-businesses state without picking one, regardless of order", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(ME_RESPONSE)),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () =>
        HttpResponse.json([business(2), business(1)]),
      ),
    );
    const { default: DashboardLayout } = await import("./layout");
    const { MultipleBusinessesState } = await import(
      "@/features/dashboard/components/MultipleBusinessesState"
    );

    const result = await DashboardLayout({ children: null });

    expect(result.type).toBe(MultipleBusinessesState);
    expect(result.props.businesses.map((b: { id: number }) => b.id).sort()).toEqual([1, 2]);
  });
});
