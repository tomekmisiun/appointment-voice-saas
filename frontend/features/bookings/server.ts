import "server-only";
import { ApiError } from "@/lib/api/errors";
import { fetchFromBackend } from "@/lib/api/server";

/**
 * Resolves a staff/service name by id, falling back to a readable
 * "#<id>" label if the record is gone (e.g. deleted after the booking was
 * made) instead of failing the whole booking-detail page over one
 * secondary lookup.
 */
export async function resolveNameOrFallback(
  path: string,
  accessToken: string,
  fallback: string,
): Promise<string> {
  try {
    const result = await fetchFromBackend<{ name: string }>(path, accessToken);
    return result.name;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return fallback;
    }
    throw error;
  }
}
