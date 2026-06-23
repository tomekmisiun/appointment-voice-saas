import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getCurrentBusinessContext } from "@/features/dashboard/current-business";
import { ApiError } from "@/lib/api/errors";
import { fetchFromBackend } from "@/lib/api/server";
import type { BookingRead } from "@/lib/api/types";
import { getSession, isAccessTokenExpired } from "@/lib/auth/server";

/**
 * Client-side proxy for the bookings list — Client Components call this,
 * never FastAPI directly (see lib/api/client.ts). A GET, so it never
 * mutates and is intentionally not CSRF-wrapped.
 *
 * Deliberately resolves the current business itself from the session
 * (via getCurrentBusinessContext, same as the dashboard layout) instead of
 * accepting a business id from the client: there is no legitimate
 * multi-business case yet (see docs/product/owner-dashboard.md), so
 * trusting a client-supplied id would only add an unnecessary place for a
 * tenant/business id to be supplied from insecure client state.
 *
 * Token freshness is handled the same way a Server Component would: if
 * the token looks expired, this returns 401 immediately rather than
 * refreshing inline, so the client's fetch wrapper sends the browser
 * through the one real refresh flow (lib/auth/actions.ts) instead of this
 * route growing its own parallel refresh logic.
 */
export async function GET(request: NextRequest) {
  const session = await getSession();

  if (!session || isAccessTokenExpired(session)) {
    return NextResponse.json(
      { error: { code: "unauthorized", message: "Session expired." } },
      { status: 401 },
    );
  }

  try {
    const context = await getCurrentBusinessContext(session.accessToken);

    if (context.kind !== "single") {
      return NextResponse.json(
        {
          error: {
            code: "no_single_business",
            message: "No single active business is available for this account.",
          },
        },
        { status: 409 },
      );
    }

    const incoming = new URL(request.url).searchParams;
    const forwarded = new URLSearchParams();
    for (const key of ["status", "staff_id", "page", "size"]) {
      const value = incoming.get(key);
      if (value !== null) {
        forwarded.set(key, value);
      }
    }

    const bookings = await fetchFromBackend<BookingRead[]>(
      `/api/v1/businesses/${context.business.id}/bookings?${forwarded.toString()}`,
      session.accessToken,
    );

    return NextResponse.json(bookings);
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json(
        { error: { code: error.code ?? "backend_error", message: error.message } },
        { status: error.status },
      );
    }
    throw error;
  }
}
