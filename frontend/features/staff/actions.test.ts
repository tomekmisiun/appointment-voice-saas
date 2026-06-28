import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../tests/mocks/server";
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

const revalidatePathMock = vi.fn();
vi.mock("next/cache", () => ({
  revalidatePath: revalidatePathMock,
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

function seedExpiredSession(): void {
  cookieStore.raw.set(
    COOKIE_NAME,
    encryptSession({
      accessToken: "stale-access-token",
      refreshToken: "stale-refresh-token",
      accessTokenExpiresAt: Math.floor(Date.now() / 1000) - 100,
    }),
  );
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

function formData(values: Record<string, string>): FormData {
  const data = new FormData();
  for (const [key, value] of Object.entries(values)) {
    data.set(key, value);
  }
  return data;
}

beforeEach(() => {
  process.env.BACKEND_API_URL = BACKEND_URL;
  process.env.SESSION_SECRET = SESSION_SECRET;
  _resetSessionSecretCacheForTests();
  cookieStore.raw.clear();
  revalidatePathMock.mockClear();
});

afterEach(() => {
  delete process.env.BACKEND_API_URL;
  delete process.env.SESSION_SECRET;
  vi.restoreAllMocks();
});

describe("createStaffAction", () => {
  it("rejects an empty name without calling the backend", async () => {
    seedValidSession();
    let backendCalled = false;
    server.use(
      http.post(`${BACKEND_URL}/api/v1/businesses/42/staff`, () => {
        backendCalled = true;
        return HttpResponse.json({});
      }),
    );
    const { createStaffAction } = await import("./actions");

    const result = await createStaffAction({ ok: true }, formData({ name: "", phone: "" }));

    expect(result.ok).toBe(false);
    expect(backendCalled).toBe(false);
  });

  it("rejects a non-admin without calling the backend", async () => {
    seedValidSession();
    let backendCalled = false;
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(meResponse("user"))),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.post(`${BACKEND_URL}/api/v1/businesses/42/staff`, () => {
        backendCalled = true;
        return HttpResponse.json({});
      }),
    );
    const { createStaffAction } = await import("./actions");

    const result = await createStaffAction({ ok: true }, formData({ name: "Alice", phone: "" }));

    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/admin/i);
    expect(backendCalled).toBe(false);
  });

  it("creates staff, forwarding a trimmed name and an empty string (not null) for a blank phone, then revalidates", async () => {
    // Regression coverage for the matching update_staff fix: create
    // doesn't have the same null-skip bug, but both actions send the same
    // normalized "" for a blank phone for consistency (see schemas.ts).
    seedValidSession();
    let receivedBody: { name?: string; phone?: string } | null = null;
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(meResponse("admin"))),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.post(`${BACKEND_URL}/api/v1/businesses/42/staff`, async ({ request }) => {
        receivedBody = (await request.json()) as { name?: string; phone?: string };
        return HttpResponse.json({
          id: 1,
          tenant_id: 1,
          business_id: 42,
          name: "Alice",
          phone: null,
          is_active: true,
          created_at: new Date().toISOString(),
        });
      }),
    );
    const { createStaffAction } = await import("./actions");

    const result = await createStaffAction({ ok: true }, formData({ name: "  Alice  ", phone: "" }));

    expect(result.ok).toBe(true);
    expect(receivedBody).toEqual({ name: "Alice", phone: "" });
    expect(revalidatePathMock).toHaveBeenCalledWith("/dashboard/staff");
  });

  it("propagates a backend error", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(meResponse("admin"))),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.post(`${BACKEND_URL}/api/v1/businesses/42/staff`, () =>
        HttpResponse.json({ error: { code: "validation_error", message: "Name too long" } }, { status: 422 }),
      ),
    );
    const { createStaffAction } = await import("./actions");

    const result = await createStaffAction({ ok: true }, formData({ name: "Alice", phone: "" }));

    expect(result.ok).toBe(false);
    expect(result.error).toBe("Name too long");
  });

  it("redirects to /login when there is no session, instead of returning a raw error", async () => {
    const { createStaffAction } = await import("./actions");

    await expect(
      createStaffAction({ ok: true }, formData({ name: "Alice", phone: "" })),
    ).rejects.toThrow("REDIRECT:/login");
  });

  it("redirects to the refresh flow when the access token looks expired", async () => {
    seedExpiredSession();
    const { createStaffAction } = await import("./actions");

    await expect(
      createStaffAction({ ok: true }, formData({ name: "Alice", phone: "" })),
    ).rejects.toThrow("REDIRECT:/auth/refresh?next=/dashboard/staff");
  });

  it("redirects to the refresh flow when FastAPI rejects an apparently-valid token with 401", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () =>
        HttpResponse.json({ error: { code: "unauthorized", message: "nope" } }, { status: 401 }),
      ),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([])),
    );
    const { createStaffAction } = await import("./actions");

    await expect(
      createStaffAction({ ok: true }, formData({ name: "Alice", phone: "" })),
    ).rejects.toThrow("REDIRECT:/auth/refresh?next=/dashboard/staff");
  });

  it("redirects to the refresh flow when the token is revoked between context resolution and the create call itself, instead of rendering 401 as a form error", async () => {
    // Regression test for a cross-provider review finding: this narrow
    // race (token looks valid in resolveAdminBusinessContext, then 401s
    // on the actual mutation) was falling into the generic ApiError
    // branch and rendering inline as if it were a normal validation
    // error, instead of going through the refresh flow like every other
    // auth failure here does.
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(meResponse("admin"))),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.post(`${BACKEND_URL}/api/v1/businesses/42/staff`, () =>
        HttpResponse.json({ error: { code: "unauthorized", message: "Token revoked" } }, { status: 401 }),
      ),
    );
    const { createStaffAction } = await import("./actions");

    await expect(
      createStaffAction({ ok: true }, formData({ name: "Alice", phone: "" })),
    ).rejects.toThrow("REDIRECT:/auth/refresh?next=/dashboard/staff");
  });
});

describe("updateStaffAction", () => {
  it("updates staff at the bound id and revalidates", async () => {
    seedValidSession();
    let receivedPath: string | null = null;
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(meResponse("admin"))),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.patch(`${BACKEND_URL}/api/v1/businesses/42/staff/7`, ({ request }) => {
        receivedPath = new URL(request.url).pathname;
        return HttpResponse.json({
          id: 7,
          tenant_id: 1,
          business_id: 42,
          name: "Bob",
          phone: "555",
          is_active: true,
          created_at: new Date().toISOString(),
        });
      }),
    );
    const { updateStaffAction } = await import("./actions");

    const result = await updateStaffAction(7, { ok: true }, formData({ name: "Bob", phone: "555" }));

    expect(result.ok).toBe(true);
    expect(receivedPath).toBe("/api/v1/businesses/42/staff/7");
    expect(revalidatePathMock).toHaveBeenCalledWith("/dashboard/staff");
  });

  it("sends an empty string, not null, when the phone field is cleared — null is silently ignored by the backend's PATCH", async () => {
    // Regression test for a cross-provider review finding: update_staff
    // only assigns `phone` when it's not None, so sending null/omitting
    // it can never clear an existing phone number through this endpoint.
    seedValidSession();
    let receivedBody: { name?: string; phone?: string } | null = null;
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(meResponse("admin"))),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.patch(`${BACKEND_URL}/api/v1/businesses/42/staff/7`, async ({ request }) => {
        receivedBody = (await request.json()) as { name?: string; phone?: string };
        return HttpResponse.json({
          id: 7,
          tenant_id: 1,
          business_id: 42,
          name: "Bob",
          phone: "",
          is_active: true,
          created_at: new Date().toISOString(),
        });
      }),
    );
    const { updateStaffAction } = await import("./actions");

    const result = await updateStaffAction(7, { ok: true }, formData({ name: "Bob", phone: "" }));

    expect(result.ok).toBe(true);
    // Exact-shape match already proves phone is "" and not null/omitted —
    // a separate `.phone` property access after a `let ... = null`
    // declaration trips the same closure-narrowing TS quirk noted
    // elsewhere in this repo (see RescheduleBookingDialog.test.tsx).
    expect(receivedBody).toEqual({ name: "Bob", phone: "" });
  });

  it("redirects to the refresh flow when the access token looks expired", async () => {
    seedExpiredSession();
    const { updateStaffAction } = await import("./actions");

    await expect(
      updateStaffAction(7, { ok: true }, formData({ name: "Bob", phone: "" })),
    ).rejects.toThrow("REDIRECT:/auth/refresh?next=/dashboard/staff");
  });
});

describe("setStaffActiveAction", () => {
  it("toggles is_active and revalidates", async () => {
    seedValidSession();
    let receivedBody: { is_active?: boolean } | null = null;
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(meResponse("admin"))),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.patch(`${BACKEND_URL}/api/v1/businesses/42/staff/7`, async ({ request }) => {
        receivedBody = (await request.json()) as { is_active?: boolean };
        return HttpResponse.json({
          id: 7,
          tenant_id: 1,
          business_id: 42,
          name: "Bob",
          phone: null,
          is_active: false,
          created_at: new Date().toISOString(),
        });
      }),
    );
    const { setStaffActiveAction } = await import("./actions");

    const result = await setStaffActiveAction(7, false);

    expect(result.ok).toBe(true);
    expect(receivedBody).toEqual({ is_active: false });
  });

  it("allows a platform_admin through, mirroring the backend's role hierarchy", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(meResponse("platform_admin"))),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([business(42)])),
      http.patch(`${BACKEND_URL}/api/v1/businesses/42/staff/7`, () =>
        HttpResponse.json({
          id: 7,
          tenant_id: 1,
          business_id: 42,
          name: "Bob",
          phone: null,
          is_active: false,
          created_at: new Date().toISOString(),
        }),
      ),
    );
    const { setStaffActiveAction } = await import("./actions");

    const result = await setStaffActiveAction(7, false);

    expect(result.ok).toBe(true);
  });

  it("rejects when no single active business is available", async () => {
    seedValidSession();
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () => HttpResponse.json(meResponse("admin"))),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([])),
    );
    const { setStaffActiveAction } = await import("./actions");

    const result = await setStaffActiveAction(7, false);

    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/business/i);
  });

  it("redirects to /login when there is no session", async () => {
    const { setStaffActiveAction } = await import("./actions");

    await expect(setStaffActiveAction(7, false)).rejects.toThrow("REDIRECT:/login");
  });
});
