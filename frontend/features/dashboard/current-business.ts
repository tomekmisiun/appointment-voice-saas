import "server-only";
import { cache } from "react";
import { fetchFromBackend } from "@/lib/api/server";
import type { BusinessRead, UserRead } from "@/lib/api/types";

export type CurrentBusinessContext =
  | { kind: "none"; user: UserRead }
  | { kind: "single"; user: UserRead; business: BusinessRead }
  | { kind: "multiple"; user: UserRead; businesses: BusinessRead[] };

/**
 * Resolves "who is signed in, and which business are they managing" for
 * the current request. There's no "my business" shortcut on the backend
 * (GET /auth/me has no tenant/business info), so this calls
 * GET /api/v1/businesses and branches explicitly on how many active
 * businesses come back — never silently picks businesses[0] (see
 * docs/product/owner-dashboard.md: multi-business owner support is out of
 * scope, so 2+ active businesses is a deliberate "not supported yet"
 * state, not a guess).
 *
 * Wrapped in React's `cache()` so the dashboard layout and the page
 * rendered inside it can both call this for the same request without a
 * second network round-trip.
 */
export const getCurrentBusinessContext = cache(
  async (accessToken: string): Promise<CurrentBusinessContext> => {
    const [user, businesses] = await Promise.all([
      fetchFromBackend<UserRead>("/api/v1/auth/me", accessToken),
      fetchFromBackend<BusinessRead[]>("/api/v1/businesses", accessToken),
    ]);

    // Defensive filter even though the endpoint already defaults to
    // excluding inactive businesses — never assume a contract detail that
    // isn't enforced here too.
    const active = businesses.filter((business) => business.is_active);

    if (active.length === 0) {
      return { kind: "none", user };
    }

    if (active.length === 1) {
      return { kind: "single", user, business: active[0] as BusinessRead };
    }

    return { kind: "multiple", user, businesses: active };
  },
);
