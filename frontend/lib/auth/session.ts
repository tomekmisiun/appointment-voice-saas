import { createCipheriv, createDecipheriv, randomBytes } from "node:crypto";

/**
 * Encrypted session cookie payload. Holds both backend JWTs server-side
 * only — the browser never sees these values (see lib/auth/server.ts).
 * `accessTokenExpiresAt` is epoch seconds, matching the JWT `exp` claim.
 */
export interface SessionPayload {
  accessToken: string;
  refreshToken: string;
  accessTokenExpiresAt: number;
}

const ALGORITHM = "aes-256-gcm";
const IV_LENGTH = 12;
const AUTH_TAG_LENGTH = 16;
const REQUIRED_KEY_BYTES = 32; // AES-256 key length

/**
 * Internal budget, well under the ~4096-byte limit browsers enforce per
 * cookie. Measured against this repo's real JWTs (access ~248B, refresh
 * ~249B) the encrypted+base64url cookie value lands around ~800B — this
 * budget leaves room for moderate token growth while still failing loudly,
 * in a test, before a real cookie would ever be silently truncated.
 */
export const SAFE_COOKIE_BYTE_LIMIT = 3072;

class SessionSecretConfigError extends Error {
  constructor(reason: string) {
    super(
      `SESSION_SECRET is ${reason}. Generate one with: openssl rand -base64 32. ` +
        "There is no development fallback — this must be set explicitly in every environment.",
    );
    this.name = "SessionSecretConfigError";
  }
}

let cachedKey: Buffer | null = null;

/**
 * Validates and returns the AES-256-GCM key derived from SESSION_SECRET.
 * Throws immediately (no fallback, ever) if the secret is missing,
 * not valid base64, or doesn't decode to exactly 32 bytes.
 */
export function getSessionSecretKey(): Buffer {
  if (cachedKey) {
    return cachedKey;
  }

  const raw = process.env.SESSION_SECRET;

  if (!raw || raw.trim().length === 0) {
    throw new SessionSecretConfigError("missing");
  }

  let decoded: Buffer;
  try {
    decoded = Buffer.from(raw, "base64");
  } catch {
    throw new SessionSecretConfigError("not valid base64");
  }

  // Buffer.from(..., "base64") never throws on malformed input — it just
  // decodes what it can — so length is the real check for "too short" or
  // "not actually base64 at all" (e.g. a plain short string decodes to
  // something shorter than 32 bytes too).
  if (decoded.length !== REQUIRED_KEY_BYTES) {
    throw new SessionSecretConfigError(
      `the wrong length once base64-decoded (expected ${REQUIRED_KEY_BYTES} bytes, got ${decoded.length})`,
    );
  }

  cachedKey = decoded;
  return cachedKey;
}

/** Test-only: clears the memoized key so tests can exercise different env values. */
export function _resetSessionSecretCacheForTests(): void {
  cachedKey = null;
}

export function encryptSession(payload: SessionPayload): string {
  const key = getSessionSecretKey();
  const iv = randomBytes(IV_LENGTH);
  const cipher = createCipheriv(ALGORITHM, key, iv);

  const plaintext = Buffer.from(JSON.stringify(payload), "utf8");
  const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final()]);
  const authTag = cipher.getAuthTag();

  return Buffer.concat([iv, ciphertext, authTag]).toString("base64url");
}

/**
 * Decrypts a session cookie value. Returns null (never throws) for any
 * tampered, expired-format, or otherwise invalid input — callers treat
 * that the same as "no session", not as a crash.
 */
export function decryptSession(cookieValue: string): SessionPayload | null {
  // Deliberately outside the try block: a misconfigured SESSION_SECRET is a
  // startup-config error that must fail loudly, not be swallowed into a
  // silent "no session" the same way a tampered cookie value is.
  const key = getSessionSecretKey();

  try {
    const combined = Buffer.from(cookieValue, "base64url");

    if (combined.length <= IV_LENGTH + AUTH_TAG_LENGTH) {
      return null;
    }

    const iv = combined.subarray(0, IV_LENGTH);
    const authTag = combined.subarray(combined.length - AUTH_TAG_LENGTH);
    const ciphertext = combined.subarray(IV_LENGTH, combined.length - AUTH_TAG_LENGTH);

    const decipher = createDecipheriv(ALGORITHM, key, iv);
    decipher.setAuthTag(authTag);

    const plaintext = Buffer.concat([decipher.update(ciphertext), decipher.final()]);
    const parsed = JSON.parse(plaintext.toString("utf8"));

    if (
      typeof parsed !== "object" ||
      parsed === null ||
      typeof parsed.accessToken !== "string" ||
      typeof parsed.refreshToken !== "string" ||
      typeof parsed.accessTokenExpiresAt !== "number"
    ) {
      return null;
    }

    return parsed as SessionPayload;
  } catch {
    return null;
  }
}
