import { NextRequest } from "next/server";
import { afterEach, describe, expect, it } from "vitest";
import { getTrustedClientIpHeaders } from "./client-ip";

afterEach(() => {
  delete process.env.BFF_TRUST_FORWARDED_HEADERS;
});

function request(headers: Record<string, string>) {
  return new NextRequest("http://localhost:3000/api/test", { headers });
}

describe("getTrustedClientIpHeaders", () => {
  it("ignores forwarded headers unless the BFF trust boundary is enabled", () => {
    expect(getTrustedClientIpHeaders(request({ "x-forwarded-for": "198.51.100.20" }))).toBeUndefined();
  });

  it("extracts and validates the original IP from a trusted proxy chain", () => {
    process.env.BFF_TRUST_FORWARDED_HEADERS = "true";
    expect(getTrustedClientIpHeaders(request({ "x-forwarded-for": "198.51.100.20, 10.0.0.1" }))).toEqual({
      "X-Forwarded-For": "198.51.100.20",
    });
  });

  it("does not forward malformed client addresses", () => {
    process.env.BFF_TRUST_FORWARDED_HEADERS = "true";
    expect(getTrustedClientIpHeaders(request({ "x-forwarded-for": "not-an-ip" }))).toBeUndefined();
  });
});
