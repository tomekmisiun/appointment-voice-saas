import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { server } from "../../tests/mocks/server";
import { ApiError } from "./errors";
import { fetchFromBackend } from "./server";

const BACKEND_URL = "http://backend.test";

beforeEach(() => {
  process.env.BACKEND_API_URL = BACKEND_URL;
});

afterEach(() => {
  delete process.env.BACKEND_API_URL;
});

describe("fetchFromBackend", () => {
  it("attaches the bearer token and parses a JSON response", async () => {
    let receivedAuth: string | null = null;
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, ({ request }) => {
        receivedAuth = request.headers.get("authorization");
        return HttpResponse.json({ id: 1, email: "owner@example.com", is_active: true, role: "admin" });
      }),
    );

    const result = await fetchFromBackend<{ email: string }>("/api/v1/auth/me", "token-123");

    expect(receivedAuth).toBe("Bearer token-123");
    expect(result.email).toBe("owner@example.com");
  });

  it("requests with cache: no-store so per-user responses are never memoized", async () => {
    // MSW's intercepted Request doesn't always surface `cache`, so this
    // asserts through the fetch init captured below instead of the request
    // MSW's handler receives.
    server.use(http.get(`${BACKEND_URL}/api/v1/businesses`, () => HttpResponse.json([])));

    const originalFetch = globalThis.fetch;
    let capturedInit: RequestInit | undefined;
    globalThis.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
      capturedInit = init;
      return originalFetch(input, init);
    }) as typeof fetch;

    try {
      await fetchFromBackend("/api/v1/businesses", "token-123");
    } finally {
      globalThis.fetch = originalFetch;
    }

    expect(capturedInit?.cache).toBe("no-store");
  });

  it("throws ApiError with the parsed envelope on a non-2xx response", async () => {
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () =>
        HttpResponse.json(
          { error: { code: "unauthorized", message: "Could not validate credentials" } },
          { status: 401 },
        ),
      ),
    );

    await expect(fetchFromBackend("/api/v1/auth/me", "bad-token")).rejects.toMatchObject({
      status: 401,
      code: "unauthorized",
    });
  });

  it("exposes isAuthError for 401 responses specifically", async () => {
    server.use(
      http.get(`${BACKEND_URL}/api/v1/auth/me`, () =>
        HttpResponse.json({ error: { code: "unauthorized", message: "nope" } }, { status: 401 }),
      ),
    );

    try {
      await fetchFromBackend("/api/v1/auth/me", "bad-token");
      expect.unreachable();
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).isAuthError).toBe(true);
    }
  });

  it("returns undefined for a 204 No Content response", async () => {
    server.use(
      http.post(`${BACKEND_URL}/api/v1/auth/logout`, () => new HttpResponse(null, { status: 204 })),
    );

    const result = await fetchFromBackend("/api/v1/auth/logout", "token-123", { method: "POST" });
    expect(result).toBeUndefined();
  });
});
