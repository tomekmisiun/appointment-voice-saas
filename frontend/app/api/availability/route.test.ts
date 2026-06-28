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

function makeRequest(query: string) {
  return new NextRequest(`http://localhost:3000/api/availability${query}`);
}

describe("GET /api/availability", () => {
  it("returns 401 without a session", async () => {
    const { GET } = await import("./route");

    const response = await GET(makeRequest(""));

    expect(response.status).toBe(401);
  });

  it("resolves the business from the session and forwards service_id/date/staff_id, ignoring a client-supplied business id", async () => {
    const accessToken = seedValidSession();
    let receivedPath: string | null = null;
    let receivedQuery: string | null = null;
    let receivedAuth: string | null = null;
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(ME_RESPONSE)),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/availability`, ({ request }) => {
        receivedAuth = request.headers.get("authorization");
        receivedPath = new URL(request.url).pathname;
        receivedQuery = new URL(request.url).search;
        return HttpResponse.json([
          { starts_at: "2026-01-15T10:00:00+00:00", ends_at: "2026-01-15T10:30:00+00:00" },
        ]);
      }),
    );
    const { GET } = await import("./route");

    const response = await GET(
      makeRequest("?service_id=10&date=2026-01-15&staff_id=1&businessId=999"),
    );
    const json = await response.json();

    expect(response.status).toBe(200);
    expect(json).toHaveLength(1);
    expect(receivedAuth).toBe(`Bearer ${accessToken}`);
    expect(receivedPath).toBe("/api/v1/businesses/42/availability");
    expect(receivedQuery).toContain("service_id=10");
    expect(receivedQuery).toContain("date=2026-01-15");
    expect(receivedQuery).toContain("staff_id=1");
    expect(receivedQuery).not.toContain("businessId");
  });

  it("propagates a backend error with the same status", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(ME_RESPONSE)),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/availability`, () =>
        HttpResponse.json({ error: { code: "validation_error", message: "bad date" } }, { status: 422 }),
      ),
    );
    const { GET } = await import("./route");

    const response = await GET(makeRequest("?service_id=10&date=not-a-date"));
    const json = await response.json();

    expect(response.status).toBe(422);
    expect(json.error.code).toBe("validation_error");
  });
});
