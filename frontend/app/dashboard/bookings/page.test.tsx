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

describe("BookingsListPage", () => {
  it("fetches staff/services for the resolved business and renders BookingsListClient with them", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(ME_RESPONSE)),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/staff`, () =>
        HttpResponse.json([{ id: 1, tenant_id: 1, business_id: 42, name: "Alice", phone: null, is_active: true, created_at: "" }]),
      ),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/services`, () =>
        HttpResponse.json([{ id: 10, tenant_id: 1, business_id: 42, name: "Haircut", duration_minutes: 30, is_active: true, price_minor_units: null, currency: null, created_at: "" }]),
      ),
    );
    const { default: BookingsListPage } = await import("./page");
    const { BookingsListClient } = await import("@/features/bookings/components/BookingsListClient");

    const result = await BookingsListPage();
    if (result === null) {
      throw new Error("expected BookingsListPage to render an element, got null");
    }

    expect(result.type).toBe(BookingsListClient);
    expect(result.props.business.id).toBe(42);
    expect(result.props.staff).toHaveLength(1);
    expect(result.props.staff[0].name).toBe("Alice");
    expect(result.props.services).toHaveLength(1);
    expect(result.props.services[0].name).toBe("Haircut");
  });

  it("redirects to /login when there is no session", async () => {
    const { default: BookingsListPage } = await import("./page");

    await expect(BookingsListPage()).rejects.toThrow("REDIRECT:/login");
  });
});
