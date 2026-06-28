import { http, HttpResponse } from "msw";
import { NextRequest } from "next/server";
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

const BACKEND_URL = "http://backend.test";
const SESSION_SECRET = Buffer.from("a".repeat(32)).toString("base64");
const COOKIE_NAME = "avs_session";
const ME_RESPONSE = { id: 1, email: "owner@example.com", is_active: true, role: "admin" };

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

function makeRequest(query = "") {
  return new NextRequest(`http://localhost:3000/api/bookings${query}`);
}

describe("GET /api/bookings", () => {
  it("returns 401 without a session", async () => {
    const { GET } = await import("./route");

    const response = await GET(makeRequest());

    expect(response.status).toBe(401);
  });

  it("returns 401 immediately on an expired token, without calling the backend", async () => {
    cookieStore.raw.set(
      COOKIE_NAME,
      encryptSession({
        accessToken: "stale",
        refreshToken: "stale-refresh",
        accessTokenExpiresAt: Math.floor(Date.now() / 1000) - 100,
      }),
    );
    let backendCalled = false;
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => {
        backendCalled = true;
        return HttpResponse.json(ME_RESPONSE);
      }),
    );
    const { GET } = await import("./route");

    const response = await GET(makeRequest());

    expect(response.status).toBe(401);
    expect(backendCalled).toBe(false);
  });

  it("returns 409 when there is no single active business, without trusting a client-supplied business id", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(ME_RESPONSE)),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(1), business(2)])),
    );
    const { GET } = await import("./route");

    // Even though a businessId is supplied here, the route must ignore it
    // entirely and resolve the business from the session itself.
    const response = await GET(makeRequest("?businessId=999"));

    expect(response.status).toBe(409);
  });

  it("forwards status/staff_id/page/size to the backend and resolves the business from the session, not the query string", async () => {
    const accessToken = seedValidSession();
    let receivedAuth: string | null = null;
    let receivedQuery: string | null = null;
    let receivedPath: string | null = null;
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(ME_RESPONSE)),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/bookings`, ({ request }) => {
        receivedAuth = request.headers.get("authorization");
        receivedQuery = new URL(request.url).search;
        receivedPath = new URL(request.url).pathname;
        return HttpResponse.json([]);
      }),
    );
    const { GET } = await import("./route");

    // businessId=999 must be ignored; the real business (42) comes from
    // getCurrentBusinessContext, not from anything the client sent.
    const response = await GET(
      makeRequest("?status=confirmed&staff_id=7&page=2&size=10&businessId=999"),
    );

    expect(response.status).toBe(200);
    expect(receivedAuth).toBe(`Bearer ${accessToken}`);
    expect(receivedPath).toBe("/api/v1/businesses/42/bookings");
    expect(receivedQuery).toContain("status=confirmed");
    expect(receivedQuery).toContain("staff_id=7");
    expect(receivedQuery).toContain("page=2");
    expect(receivedQuery).toContain("size=10");
    expect(receivedQuery).not.toContain("businessId");
  });

  it("propagates a backend error as the same status with the error envelope", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(ME_RESPONSE)),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(5)])),
      http.get(`${BACKEND_URL}/api/v1/businesses/5/bookings`, () =>
        HttpResponse.json({ error: { code: "validation_error", message: "bad status" } }, { status: 422 }),
      ),
    );
    const { GET } = await import("./route");

    const response = await GET(makeRequest("?status=not-a-real-status"));
    const json = await response.json();

    expect(response.status).toBe(422);
    expect(json.error.code).toBe("validation_error");
  });
});
