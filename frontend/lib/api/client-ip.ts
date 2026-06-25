import "server-only";
import { isIP } from "node:net";

/**
 * Returns one validated client address only when the BFF is deployed behind
 * a trusted proxy that replaces forwarded headers. Without that explicit
 * trust boundary, browser-supplied forwarding headers are ignored.
 */
export function getTrustedClientIpHeaders(request: Request): Record<string, string> | undefined {
  if (process.env.BFF_TRUST_FORWARDED_HEADERS !== "true") {
    return undefined;
  }

  const forwardedFor = request.headers.get("x-forwarded-for");
  const candidate = forwardedFor?.split(",")[0]?.trim() || request.headers.get("x-real-ip")?.trim();

  if (!candidate || isIP(candidate) === 0) {
    return undefined;
  }

  return { "X-Forwarded-For": candidate };
}
