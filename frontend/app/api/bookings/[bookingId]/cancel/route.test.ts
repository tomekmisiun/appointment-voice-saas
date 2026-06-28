import { http, HttpResponse } from "msw";
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../../../../tests/mocks/server";
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

function meResponse(role: string) {
  return { id: 1, email: "owner@example.com", is_active: true, role };
}

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
  return new NextRequest("http://localhost:3000/api/bookings/1/cancel", {
    method: "POST",
    headers: { origin: APP_ORIGIN, "content-type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
}

function routeContext(bookingId = "1") {
  return { params: Promise.resolve({ bookingId }) };
}

describe("POST /api/bookings/[bookingId]/cancel", () => {
  it("rejects a cross-origin request before touching the backend", async () => {
    const { POST } = await import("./route");
    let backendCalled = false;
    server.use(
      http.post(`${BACKEND_URL}/api/v1/businesses/42/bookings/1/cancel`, () => {
        backendCalled = true;
        return HttpResponse.json({});
      }),
    );

    const response = await POST(makeRequest({}, { origin: "https://evil.example" }), routeContext());

    expect(response.status).toBe(403);
    expect(backendCalled).toBe(false);
  });

  it("returns 401 without a session", async () => {
    const { POST } = await import("./route");

    const response = await POST(makeRequest({}), routeContext());

    expect(response.status).toBe(401);
  });

  it("returns 403 for a non-admin user, without calling the backend", async () => {
    seedValidSession();
    let backendCalled = false;
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(meResponse("user"))),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.post(`${BACKEND_URL}/api/v1/businesses/42/bookings/1/cancel`, () => {
        backendCalled = true;
        return HttpResponse.json({});
      }),
    );
    const { POST } = await import("./route");

    const response = await POST(makeRequest({}), routeContext());
    const json = await response.json();

    expect(response.status).toBe(403);
    expect(json.error.code).toBe("forbidden");
    expect(backendCalled).toBe(false);
  });

  it("allows a platform_admin through, mirroring the backend's role hierarchy", async () => {
    const accessToken = seedValidSession();
    let receivedAuth: string | null = null;
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(meResponse("platform_admin"))),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.post(`${BACKEND_URL}/api/v1/businesses/42/bookings/1/cancel`, ({ request }) => {
        receivedAuth = request.headers.get("authorization");
        return HttpResponse.json({ id: 1, status: "cancelled" });
      }),
    );
    const { POST } = await import("./route");

    const response = await POST(makeRequest({}), routeContext());

    expect(response.status).toBe(200);
    expect(receivedAuth).toBe(`Bearer ${accessToken}`);
  });

  it("returns 400 for a non-numeric booking id, without resolving the business", async () => {
    seedValidSession();
    const { POST } = await import("./route");

    const response = await POST(makeRequest({}), routeContext("not-a-number"));

    expect(response.status).toBe(400);
  });

  it("cancels successfully for an admin and forwards the reason", async () => {
    const accessToken = seedValidSession();
    let receivedBody: { reason?: string } | null = null;
    let receivedAuth: string | null = null;
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(meResponse("admin"))),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.post(`${BACKEND_URL}/api/v1/businesses/42/bookings/1/cancel`, async ({ request }) => {
        receivedAuth = request.headers.get("authorization");
        receivedBody = (await request.json()) as { reason?: string };
        return HttpResponse.json({
          id: 1,
          tenant_id: 1,
          business_id: 42,
          customer_id: 7,
          service_id: 10,
          staff_id: 1,
          starts_at: "2026-01-15T10:00:00+00:00",
          ends_at: "2026-01-15T10:30:00+00:00",
          status: "cancelled",
          source: "api",
          cancel_reason: "Customer requested",
          created_at: "2026-01-10T00:00:00+00:00",
        });
      }),
    );
    const { POST } = await import("./route");

    const response = await POST(makeRequest({ reason: "Customer requested" }), routeContext());
    const json = await response.json();

    expect(response.status).toBe(200);
    expect(json.status).toBe("cancelled");
    expect(receivedAuth).toBe(`Bearer ${accessToken}`);
    expect(receivedBody).toEqual({ reason: "Customer requested" });
  });

  it("propagates a backend conflict (e.g. already cancelled) as the same status", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(meResponse("admin"))),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.post(`${BACKEND_URL}/api/v1/businesses/42/bookings/1/cancel`, () =>
        HttpResponse.json({ error: { code: "conflict", message: "Already cancelled" } }, { status: 409 }),
      ),
    );
    const { POST } = await import("./route");

    const response = await POST(makeRequest({}), routeContext());
    const json = await response.json();

    expect(response.status).toBe(409);
    expect(json.error.code).toBe("conflict");
  });
});
