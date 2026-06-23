/**
 * Reads the `exp` claim out of a JWT without verifying its signature.
 * Only used to size the session cookie's Max-Age — FastAPI remains the
 * sole authority that verifies the signature on every real request, so an
 * unverified read here never affects an authorization decision.
 */
export function readJwtExpiry(token: string): number | null {
  const segments = token.split(".");
  if (segments.length !== 3) {
    return null;
  }

  try {
    const payloadJson = Buffer.from(segments[1] ?? "", "base64url").toString("utf8");
    const payload = JSON.parse(payloadJson);
    return typeof payload.exp === "number" ? payload.exp : null;
  } catch {
    return null;
  }
}
