import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { isSameOriginRequest, withCsrfProtection } from "./csrf";

const APP_ORIGIN = "http://localhost:3000";

beforeEach(() => {
  process.env.APP_ORIGIN = APP_ORIGIN;
});

afterEach(() => {
  delete process.env.APP_ORIGIN;
});

function makeRequest(headers: Record<string, string>): NextRequest {
  return new NextRequest(`${APP_ORIGIN}/api/auth/login`, {
    method: "POST",
    headers,
  });
}

describe("isSameOriginRequest", () => {
  it("accepts a matching Origin header", () => {
    expect(isSameOriginRequest(makeRequest({ origin: APP_ORIGIN }))).toBe(true);
  });

  it("rejects a mismatched Origin header", () => {
    expect(isSameOriginRequest(makeRequest({ origin: "https://evil.example" }))).toBe(false);
  });

  it("falls back to a matching Referer when Origin is absent", () => {
    expect(
      isSameOriginRequest(makeRequest({ referer: `${APP_ORIGIN}/login` })),
    ).toBe(true);
  });

  it("rejects a mismatched Referer when Origin is absent", () => {
    expect(
      isSameOriginRequest(makeRequest({ referer: "https://evil.example/login" })),
    ).toBe(false);
  });

  it("rejects when both Origin and Referer are absent", () => {
    expect(isSameOriginRequest(makeRequest({}))).toBe(false);
  });
});

describe("withCsrfProtection", () => {
  it("returns 403 and never invokes the handler for a cross-origin request", async () => {
    let handlerCalled = false;
    const handler = withCsrfProtection(async () => {
      handlerCalled = true;
      return new Response(JSON.stringify({ ok: true }));
    });

    const response = await handler(makeRequest({ origin: "https://evil.example" }));

    expect(response.status).toBe(403);
    expect(handlerCalled).toBe(false);
    const body = await response.json();
    expect(body.error.code).toBe("csrf_origin_mismatch");
  });

  it("invokes the handler for a same-origin request", async () => {
    let handlerCalled = false;
    const handler = withCsrfProtection(async () => {
      handlerCalled = true;
      return new Response(JSON.stringify({ ok: true }));
    });

    const response = await handler(makeRequest({ origin: APP_ORIGIN }));

    expect(response.status).toBe(200);
    expect(handlerCalled).toBe(true);
  });
});
