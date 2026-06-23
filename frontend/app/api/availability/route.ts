import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getCurrentBusinessContext } from "@/features/dashboard/current-business";
import { ApiError } from "@/lib/api/errors";
import { fetchFromBackend } from "@/lib/api/server";
import type { AvailabilitySlot } from "@/lib/api/types";
import { getSession, isAccessTokenExpired } from "@/lib/auth/server";

/**
 * Client-side proxy for availability lookups (used by the reschedule
 * dialog's slot picker). Resolves the business from the session, exactly
 * like the bookings list proxy — never from client input. `service_id`,
 * `date`, and `staff_id` ARE taken from the client: unlike business_id,
 * these are ordinary query filters scoped within the already-resolved
 * business, not a tenant-isolation boundary.
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
    for (const key of ["service_id", "date", "staff_id"]) {
      const value = incoming.get(key);
      if (value !== null) {
        forwarded.set(key, value);
      }
    }

    const slots = await fetchFromBackend<AvailabilitySlot[]>(
      `/api/v1/businesses/${context.business.id}/availability?${forwarded.toString()}`,
      session.accessToken,
    );

    return NextResponse.json(slots);
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
