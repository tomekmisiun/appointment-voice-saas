import "server-only";

const inFlight = new Map<string, Promise<unknown>>();

/**
 * De-duplication for concurrent refresh attempts sharing the same starting
 * refresh token, within a single server process: a Client Component effect
 * firing twice under React Strict Mode, or two tabs/requests landing on the
 * same Next.js instance at nearly the same time, share the one in-flight
 * network call and either both succeed together or both fail together.
 * This is what actually prevents the backend's single-use, atomically
 * rotated refresh token from being raced into corrupting the session — see
 * refreshSessionAction's catch block for why there is deliberately no
 * other "did someone else already win" check.
 *
 * Known, undefended gap: this Map is process-local. A horizontally scaled
 * deployment (multiple Next.js instances behind a load balancer without
 * sticky sessions) can still have two genuinely separate processes race
 * the same starting token — this app has no shared cross-instance lock
 * (e.g. Redis-backed) to cover that case. Single-instance deployments
 * (including local dev) are fully covered.
 */
export async function singleFlightRefresh<T>(key: string, run: () => Promise<T>): Promise<T> {
  const existing = inFlight.get(key);
  if (existing) {
    return existing as Promise<T>;
  }

  const promise = run().finally(() => {
    inFlight.delete(key);
  });

  inFlight.set(key, promise);
  return promise as Promise<T>;
}
