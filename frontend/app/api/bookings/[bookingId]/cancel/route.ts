import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getCurrentBusinessContext } from "@/features/dashboard/current-business";
import { ApiError } from "@/lib/api/errors";
import { fetchFromBackend } from "@/lib/api/server";
import type { BookingCancelRequest, BookingRead } from "@/lib/api/types";
import { withCsrfProtection } from "@/lib/auth/csrf";
import { roleIncludes } from "@/lib/auth/roles";
import { getSession, isAccessTokenExpired } from "@/lib/auth/server";

/**
 * Client-side proxy for booking cancellation. CSRF-protected (state-
 * changing). Resolves the business from the session, exactly like the
 * bookings list proxy — never from anything the client sends.
 *
 * Checks the admin role server-side before calling the backend, even
 * though the UI already hides the cancel action for non-admins: the UI
 * hiding it is a UX nicety, not the security boundary. The backend itself
 * also enforces this (require_role("admin")) — this check just gives a
 * clean 403 instead of letting the backend's own enforcement do it. Uses
 * roleIncludes(), not a strict `=== "admin"`, so a platform_admin (which
 * the backend's own role hierarchy already grants admin access to) isn't
 * incorrectly rejected here before ever reaching the backend.
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
          { error: { code: "forbidden", message: "Only an admin can cancel a booking." } },
          { status: 403 },
        );
      }

      let body: BookingCancelRequest = {};
      try {
        const raw = await request.text();
        body = raw ? (JSON.parse(raw) as BookingCancelRequest) : {};
      } catch {
        return NextResponse.json(
          { error: { code: "invalid_request", message: "Request body must be valid JSON." } },
          { status: 400 },
        );
      }

      const booking = await fetchFromBackend<BookingRead>(
        `/api/v1/businesses/${context.business.id}/bookings/${bookingId}/cancel`,
        session.accessToken,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );

      return NextResponse.json(booking);
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
