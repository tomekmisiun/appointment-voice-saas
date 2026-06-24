import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../tests/mocks/server";

vi.mock("next/navigation", () => ({
  redirect: vi.fn((path: string) => {
    throw new Error(`REDIRECT:${path}`);
  }),
}));

const BACKEND_URL = "http://backend.test";

beforeEach(() => {
  process.env.BACKEND_API_URL = BACKEND_URL;
});

afterEach(() => {
  delete process.env.BACKEND_API_URL;
  vi.restoreAllMocks();
});

describe("getCurrentBusinessContextOrRefresh", () => {
  it("returns the resolved context on success, without redirecting", async () => {
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () =>
        HttpResponse.json({ id: 1, email: "owner@example.com", is_active: true, role: "admin" }),
      ),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([])),
    );
    const { getCurrentBusinessContextOrRefresh } = await import("./current-business");

    const result = await getCurrentBusinessContextOrRefresh("token-unique-1", "/dashboard/anything");

    expect(result.kind).toBe("none");
  });

  it("redirects through /auth/refresh with the given next path on a 401", async () => {
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () =>
        HttpResponse.json({ error: { code: "unauthorized", message: "nope" } }, { status: 401 }),
      ),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([])),
    );
    const { getCurrentBusinessContextOrRefresh } = await import("./current-business");

    await expect(
      getCurrentBusinessContextOrRefresh("token-unique-2", "/dashboard/services"),
    ).rejects.toThrow("REDIRECT:/auth/refresh?next=/dashboard/services");
  });

  it("re-throws a non-auth backend error instead of redirecting", async () => {
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () =>
        HttpResponse.json({ error: { code: "backend_error", message: "boom" } }, { status: 500 }),
      ),
      http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([])),
    );
    const { getCurrentBusinessContextOrRefresh } = await import("./current-business");

    await expect(
      getCurrentBusinessContextOrRefresh("token-unique-3", "/dashboard/anything"),
    ).rejects.toThrow("boom");
  });
});
