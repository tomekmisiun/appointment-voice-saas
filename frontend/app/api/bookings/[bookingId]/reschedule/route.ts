import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getCurrentBusinessContext } from "@/features/dashboard/current-business";
import { ApiError } from "@/lib/api/errors";
import { fetchFromBackend } from "@/lib/api/server";
import type { BookingRead, BookingRescheduleRequest } from "@/lib/api/types";
import { withCsrfProtection } from "@/lib/auth/csrf";
import { roleIncludes } from "@/lib/auth/roles";
import { getSession, isAccessTokenExpired } from "@/lib/auth/server";

/**
 * Client-side proxy for booking rescheduling. CSRF-protected. Resolves
 * the business from the session and re-checks the admin role (via
 * roleIncludes, not a strict string match — see lib/auth/roles.ts and the
 * cancel route for why) — same pattern as cancellation.
 *
 * The backend's reschedule cancels the old booking and creates a new one
 * at the new time (the calendar adapter can't update an event's time in
 * place) — the response is a *different* booking with a new id. Callers
 * must navigate to that new id, not assume the current URL still points
 * at a live booking.
 */
export const POST = withCsrfProtection(
  async (request: NextRequest, routeContext: { params: Promise<{ bookingId: string }> }) => {
    const session = await getSession();

    if (!session || isAccessTokenExpired(session)) {
      return NextResponse.json(
        { error: { code: "unauthorized", message: "Session expired." } },
        { status: 401 },
      );
    }

    const { bookingId: bookingIdParam } = await routeContext.params;
    const bookingId = Number(bookingIdParam);
    if (!Number.isInteger(bookingId) || bookingId <= 0) {
      return NextResponse.json(
        { error: { code: "invalid_request", message: "Invalid booking id." } },
        { status: 400 },
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

      if (!roleIncludes(context.user.role, "admin")) {
        return NextResponse.json(
          { error: { code: "forbidden", message: "Only an admin can reschedule a booking." } },
          { status: 403 },
        );
      }

      let body: BookingRescheduleRequest;
      try {
        body = JSON.parse(await request.text()) as BookingRescheduleRequest;
      } catch {
        return NextResponse.json(
          { error: { code: "invalid_request", message: "Request body must be valid JSON." } },
          { status: 400 },
        );
      }

      if (!body.new_starts_at) {
        return NextResponse.json(
          { error: { code: "invalid_request", message: "new_starts_at is required." } },
          { status: 400 },
        );
      }

      const newBooking = await fetchFromBackend<BookingRead>(
        `/api/v1/businesses/${context.business.id}/bookings/${bookingId}/reschedule`,
        session.accessToken,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );

      return NextResponse.json(newBooking);
    } catch (error) {
      if (error instanceof ApiError) {
        return NextResponse.json(
          { error: { code: error.code ?? "backend_error", message: error.message } },
          { status: error.status },
        );
      }
      throw error;
    }
  },
);
