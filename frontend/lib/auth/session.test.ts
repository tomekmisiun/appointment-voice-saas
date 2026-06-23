import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  SAFE_COOKIE_BYTE_LIMIT,
  _resetSessionSecretCacheForTests,
  decryptSession,
  encryptSession,
  getSessionSecretKey,
  type SessionPayload,
} from "./session";

const VALID_SECRET = Buffer.from("a".repeat(32)).toString("base64");
const originalEnv = process.env.SESSION_SECRET;

function setSecret(value: string | undefined) {
  if (value === undefined) {
    delete process.env.SESSION_SECRET;
  } else {
    process.env.SESSION_SECRET = value;
  }
  _resetSessionSecretCacheForTests();
}

beforeEach(() => {
  setSecret(VALID_SECRET);
});

afterEach(() => {
  setSecret(originalEnv);
});

describe("SESSION_SECRET validation", () => {
  it("throws a clear error when missing", () => {
    setSecret(undefined);
    expect(() => getSessionSecretKey()).toThrowError(/SESSION_SECRET is missing/);
  });

  it("throws a clear error when too short", () => {
    setSecret(Buffer.from("short").toString("base64"));
    expect(() => getSessionSecretKey()).toThrowError(/wrong length/);
  });

  it("throws a clear error when too long", () => {
    setSecret(Buffer.from("a".repeat(64)).toString("base64"));
    expect(() => getSessionSecretKey()).toThrowError(/wrong length/);
  });

  it("never falls back to a default secret in any environment", () => {
    setSecret(undefined);
    // Same behavior regardless of NODE_ENV — no dev-only fallback exists.
    expect(() => getSessionSecretKey()).toThrow();
  });

  it("accepts a properly sized base64-encoded 32-byte secret", () => {
    expect(() => getSessionSecretKey()).not.toThrow();
  });
});

describe("encryptSession / decryptSession", () => {
  const payload: SessionPayload = {
    accessToken: "access-token-value",
    refreshToken: "refresh-token-value",
    accessTokenExpiresAt: Math.floor(Date.now() / 1000) + 1800,
  };

  it("round-trips a payload", () => {
    const cookie = encryptSession(payload);
    expect(decryptSession(cookie)).toEqual(payload);
  });

  it("returns null for a tampered cookie value", () => {
    const cookie = encryptSession(payload);
    const tampered = cookie.slice(0, -4) + "AAAA";
    expect(decryptSession(tampered)).toBeNull();
  });

  it("returns null for garbage input", () => {
    expect(decryptSession("not-a-valid-cookie")).toBeNull();
  });

  it("returns null when decrypted with the wrong key (different secret)", () => {
    const cookie = encryptSession(payload);
    setSecret(Buffer.from("b".repeat(32)).toString("base64"));
    expect(decryptSession(cookie)).toBeNull();
  });

  it("propagates a misconfigured SESSION_SECRET instead of returning null", () => {
    const cookie = encryptSession(payload);
    setSecret(undefined);
    expect(() => decryptSession(cookie)).toThrowError(/SESSION_SECRET is missing/);
  });
});

describe("session cookie size budget", () => {
  it("stays under the safe cookie byte limit even with padded tokens", () => {
    // Real tokens minted by this repo's backend measure ~248-249 bytes
    // (HS256 JWT with {sub, tenant_id, token_version, exp, type, jti}).
    // Pad to ~2x that to absorb future claim growth and still prove the
    // budget holds, rather than only testing today's exact size.
    const paddedPayload: SessionPayload = {
      accessToken: "x".repeat(500),
      refreshToken: "y".repeat(500),
      accessTokenExpiresAt: Math.floor(Date.now() / 1000) + 1800,
    };

    const cookie = encryptSession(paddedPayload);
    expect(cookie.length).toBeLessThan(SAFE_COOKIE_BYTE_LIMIT);
  });
});
