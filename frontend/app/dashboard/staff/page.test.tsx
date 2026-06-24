import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../../tests/mocks/server";
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

vi.mock("next/navigation", () => ({
  redirect: vi.fn((path: string) => {
    throw new Error(`REDIRECT:${path}`);
  }),
}));

vi.mock("@/features/staff/actions", () => ({
  createStaffAction: vi.fn(),
  updateStaffAction: vi.fn(),
  setStaffActiveAction: vi.fn(),
}));

const BACKEND_URL = "http://backend.test";
const SESSION_SECRET = Buffer.from("a".repeat(32)).toString("base64");
const COOKIE_NAME = "avs_session";

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

function business(id: number) {
  return {
    id,
    tenant_id: 1,
    name: `Business ${id}`,
    timezone: "Europe/Warsaw",
    phone: null,
    is_active: true,
    transfer_enabled: false,
    transfer_destination_policy: "business_phone",
    booking_mode: "internal_booking",
    external_booking_url: null,
    external_booking_label: null,
    external_booking_provider: null,
    subscription_plan: "full_booking",
    created_at: new Date().toISOString(),
  };
}

function meResponse(role: string) {
  return { id: 1, email: "owner@example.com", is_active: true, role };
}

function staffMember(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    tenant_id: 1,
    business_id: 42,
    name: "Alice",
    phone: null,
    is_active: true,
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

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

describe("StaffPage", () => {
  it("renders the staff list with Add/Edit/Deactivate controls for an admin", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(meResponse("admin"))),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/staff`, () => HttpResponse.json([staffMember()])),
    );
    const { default: StaffPage } = await import("./page");

    const result = await StaffPage({ searchParams: Promise.resolve({}) });
    render(result);

    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add staff" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Deactivate" })).toBeInTheDocument();
  });

  it("hides management controls for a non-admin", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(meResponse("user"))),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/staff`, () => HttpResponse.json([staffMember()])),
    );
    const { default: StaffPage } = await import("./page");

    const result = await StaffPage({ searchParams: Promise.resolve({}) });
    render(result);

    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add staff" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
  });

  it("shows an empty state when there is no staff", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(meResponse("admin"))),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/staff`, () => HttpResponse.json([])),
    );
    const { default: StaffPage } = await import("./page");

    const result = await StaffPage({ searchParams: Promise.resolve({}) });
    render(result);

    expect(screen.getByText(/no staff configured/i)).toBeInTheDocument();
  });

  it("forwards page and include_inactive to the backend from searchParams", async () => {
    seedValidSession();
    let receivedQuery: string | null = null;
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(meResponse("admin"))),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/staff`, ({ request }) => {
        receivedQuery = new URL(request.url).search;
        return HttpResponse.json([staffMember({ is_active: false })]);
      }),
    );
    const { default: StaffPage } = await import("./page");

    const result = await StaffPage({
      searchParams: Promise.resolve({ page: "2", includeInactive: "true" }),
    });
    render(result);

    expect(receivedQuery).toContain("page=2");
    expect(receivedQuery).toContain("include_inactive=true");
    expect(screen.getByText("Inactive")).toBeInTheDocument();
  });

  it("falls back to page 1 for a non-integer page value instead of forwarding it to the backend's int query param", async () => {
    // Regression test for a cross-provider review finding: "1.5",
    // "Infinity", etc. are truthy and non-NaN, so a naive `Number(...) ||
    // 1` lets them through unchanged, and FastAPI 422s on a non-integer
    // `page` query param.
    seedValidSession();
    let receivedQuery: string | null = null;
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(meResponse("admin"))),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/staff`, ({ request }) => {
        receivedQuery = new URL(request.url).search;
        return HttpResponse.json([staffMember()]);
      }),
    );
    const { default: StaffPage } = await import("./page");

    const result = await StaffPage({ searchParams: Promise.resolve({ page: "1.5" }) });
    render(result);

    expect(receivedQuery).toContain("page=1");
    expect(receivedQuery).not.toContain("page=1.5");
  });

  it("redirects to the refresh flow when the staff list request itself returns 401", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(meResponse("admin"))),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/staff`, () =>
        HttpResponse.json({ error: { code: "unauthorized", message: "nope" } }, { status: 401 }),
      ),
    );
    const { default: StaffPage } = await import("./page");

    await expect(StaffPage({ searchParams: Promise.resolve({}) })).rejects.toThrow(
      "REDIRECT:/auth/refresh?next=/dashboard/staff",
    );
  });

  it("redirects to the refresh flow when resolving the business context itself returns 401", async () => {
    // Regression test for a cross-provider review finding: this call
    // (distinct from the staff-list fetch above) wasn't wrapped in the
    // same auth-error redirect at all, so a 401 here fell through to the
    // generic error boundary. Now shared via
    // getCurrentBusinessContextOrRefresh — see current-business.ts.
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () =>
        HttpResponse.json({ error: { code: "unauthorized", message: "nope" } }, { status: 401 }),
      ),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([])),
    );
    const { default: StaffPage } = await import("./page");

    await expect(StaffPage({ searchParams: Promise.resolve({}) })).rejects.toThrow(
      "REDIRECT:/auth/refresh?next=/dashboard/staff",
    );
  });

  it("redirects to /login when there is no session", async () => {
    const { default: StaffPage } = await import("./page");

    await expect(StaffPage({ searchParams: Promise.resolve({}) })).rejects.toThrow("REDIRECT:/login");
  });
});
