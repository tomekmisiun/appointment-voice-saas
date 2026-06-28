import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../../../tests/mocks/server";
import { _resetSessionSecretCacheForTests, encryptSession } from "@/lib/auth/session";

// The detail page may render <CancelBookingDialog>, a Client Component
// that calls useMutation() — it needs a QueryClientProvider even in these
// otherwise-Server-Component-only tests.
function renderPage(element: React.ReactElement | null) {
  if (element === null) {
    throw new Error("expected BookingDetailPage to render an element, got null");
  }
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{element}</QueryClientProvider>);
}

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
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
  notFound: vi.fn(() => {
    throw new Error("NOT_FOUND");
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

function booking(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    tenant_id: 1,
    business_id: 42,
    customer_id: 7,
    service_id: 10,
    staff_id: 1,
    starts_at: "2026-01-15T10:00:00+00:00",
    ends_at: "2026-01-15T10:30:00+00:00",
    status: "confirmed",
    source: "api",
    cancel_reason: null,
    created_at: "2026-01-10T00:00:00+00:00",
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

describe("BookingDetailPage", () => {
  it("renders booking details with resolved staff/service names", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(ME_RESPONSE)),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/bookings/1`, () => HttpResponse.json(booking())),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/services/10`, () =>
        HttpResponse.json({ id: 10, name: "Haircut" }),
      ),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/staff/1`, () =>
        HttpResponse.json({ id: 1, name: "Alice" }),
      ),
    );
    const { default: BookingDetailPage } = await import("./page");

    const result = await BookingDetailPage({ params: Promise.resolve({ bookingId: "1" }) });
    renderPage(result);

    expect(screen.getByText("Haircut")).toBeInTheDocument();
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText(/Customer #7/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel booking" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reschedule" })).toBeInTheDocument();
  });

  it("hides the cancel action for a non-admin user", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json({ ...ME_RESPONSE, role: "user" })),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/bookings/1`, () => HttpResponse.json(booking())),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/services/10`, () =>
        HttpResponse.json({ id: 10, name: "Haircut" }),
      ),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/staff/1`, () =>
        HttpResponse.json({ id: 1, name: "Alice" }),
      ),
    );
    const { default: BookingDetailPage } = await import("./page");

    const result = await BookingDetailPage({ params: Promise.resolve({ bookingId: "1" }) });
    renderPage(result);

    expect(screen.queryByRole("button", { name: "Cancel booking" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reschedule" })).not.toBeInTheDocument();
  });

  it("shows the cancel action for a platform_admin, mirroring the backend's role hierarchy", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () =>
        HttpResponse.json({ ...ME_RESPONSE, role: "platform_admin" }),
      ),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/bookings/1`, () => HttpResponse.json(booking())),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/services/10`, () =>
        HttpResponse.json({ id: 10, name: "Haircut" }),
      ),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/staff/1`, () =>
        HttpResponse.json({ id: 1, name: "Alice" }),
      ),
    );
    const { default: BookingDetailPage } = await import("./page");

    const result = await BookingDetailPage({ params: Promise.resolve({ bookingId: "1" }) });
    renderPage(result);

    expect(screen.getByRole("button", { name: "Cancel booking" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reschedule" })).toBeInTheDocument();
  });

  it("hides the cancel action for an already-cancelled booking", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(ME_RESPONSE)),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/bookings/1`, () =>
        HttpResponse.json(booking({ status: "cancelled", cancel_reason: "Already gone" })),
      ),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/services/10`, () =>
        HttpResponse.json({ id: 10, name: "Haircut" }),
      ),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/staff/1`, () =>
        HttpResponse.json({ id: 1, name: "Alice" }),
      ),
    );
    const { default: BookingDetailPage } = await import("./page");

    const result = await BookingDetailPage({ params: Promise.resolve({ bookingId: "1" }) });
    renderPage(result);

    expect(screen.queryByRole("button", { name: "Cancel booking" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reschedule" })).not.toBeInTheDocument();
    expect(screen.getByText("Already gone")).toBeInTheDocument();
  });

  it("falls back to a numbered label when the staff record is gone", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(ME_RESPONSE)),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/bookings/1`, () => HttpResponse.json(booking())),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/services/10`, () =>
        HttpResponse.json({ id: 10, name: "Haircut" }),
      ),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/staff/1`, () =>
        HttpResponse.json({ error: { code: "not_found", message: "gone" } }, { status: 404 }),
      ),
    );
    const { default: BookingDetailPage } = await import("./page");

    const result = await BookingDetailPage({ params: Promise.resolve({ bookingId: "1" }) });
    renderPage(result);

    expect(screen.getByText("Staff #1")).toBeInTheDocument();
  });

  it("shows 'Any available' when the booking has no specific staff", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(ME_RESPONSE)),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/bookings/1`, () =>
        HttpResponse.json(booking({ staff_id: null })),
      ),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/services/10`, () =>
        HttpResponse.json({ id: 10, name: "Haircut" }),
      ),
    );
    const { default: BookingDetailPage } = await import("./page");

    const result = await BookingDetailPage({ params: Promise.resolve({ bookingId: "1" }) });
    renderPage(result);

    expect(screen.getByText("Any available")).toBeInTheDocument();
  });

  it("calls notFound() for a non-existent booking", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(ME_RESPONSE)),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.get(`${BACKEND_URL}/api/v1/businesses/42/bookings/999`, () =>
        HttpResponse.json({ error: { code: "not_found", message: "gone" } }, { status: 404 }),
      ),
    );
    const { default: BookingDetailPage } = await import("./page");

    await expect(
      BookingDetailPage({ params: Promise.resolve({ bookingId: "999" }) }),
    ).rejects.toThrow("NOT_FOUND");
  });

  it("calls notFound() for a non-numeric booking id instead of querying the backend", async () => {
    seedValidSession();
    let backendCalled = false;
    server.use(
      http.get(`${BACKEND_URL}/api/v1/businesses/42/bookings/:id`, () => {
        backendCalled = true;
        return HttpResponse.json(booking());
      }),
    );
    const { default: BookingDetailPage } = await import("./page");

    await expect(
      BookingDetailPage({ params: Promise.resolve({ bookingId: "not-a-number" }) }),
    ).rejects.toThrow("NOT_FOUND");
    expect(backendCalled).toBe(false);
  });

  it("redirects to /login when there is no session", async () => {
    const { default: BookingDetailPage } = await import("./page");

    await expect(
      BookingDetailPage({ params: Promise.resolve({ bookingId: "1" }) }),
    ).rejects.toThrow("REDIRECT:/login");
  });
});
