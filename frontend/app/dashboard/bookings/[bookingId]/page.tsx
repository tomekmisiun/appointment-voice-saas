import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { BookingStatusBadge } from "@/features/bookings/components/BookingStatusBadge";
import { CancelBookingDialog } from "@/features/bookings/components/CancelBookingDialog";
import { RescheduleBookingDialog } from "@/features/bookings/components/RescheduleBookingDialog";
import { resolveNameOrFallback } from "@/features/bookings/server";
import { formatInBusinessTimezone } from "@/features/bookings/utils";
import { getCurrentBusinessContext } from "@/features/dashboard/current-business";
import { ApiError } from "@/lib/api/errors";
import { fetchFromBackend } from "@/lib/api/server";
import type { BookingRead } from "@/lib/api/types";
import { roleIncludes } from "@/lib/auth/roles";
import { getSession } from "@/lib/auth/server";

export default async function BookingDetailPage({
  params,
}: {
  params: Promise<{ bookingId: string }>;
}) {
  const { bookingId: bookingIdParam } = await params;
  const bookingId = Number(bookingIdParam);
  if (!Number.isInteger(bookingId) || bookingId <= 0) {
    notFound();
  }

  const session = await getSession();
  if (!session) {
    redirect("/login");
  }

  const context = await getCurrentBusinessContext(session.accessToken);
  if (context.kind !== "single") {
    return null;
  }

  let booking: BookingRead;
  try {
    booking = await fetchFromBackend<BookingRead>(
      `/api/v1/businesses/${context.business.id}/bookings/${bookingId}`,
      session.accessToken,
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    if (error instanceof ApiError && error.isAuthError) {
      redirect("/auth/refresh?next=/dashboard/bookings");
    }
    throw error;
  }

  const [serviceName, staffName] = await Promise.all([
    resolveNameOrFallback(
      `/api/v1/businesses/${context.business.id}/services/${booking.service_id}`,
      session.accessToken,
      `Service #${booking.service_id}`,
    ),
    booking.staff_id
      ? resolveNameOrFallback(
          `/api/v1/businesses/${context.business.id}/staff/${booking.staff_id}`,
          session.accessToken,
          `Staff #${booking.staff_id}`,
        )
      : Promise.resolve("Any available"),
  ]);

  // Role check mirrors the proxy routes' own checks (the real boundary —
  // the backend enforces require_role("admin") regardless of this UI),
  // including the role hierarchy (platform_admin counts as admin too —
  // see lib/auth/roles.ts). Hiding these actions for an insufficient role
  // or an already-cancelled booking is a UX nicety, not the security
  // control. Cancel and reschedule share the same eligibility rule.
  const canModify = roleIncludes(context.user.role, "admin") && booking.status === "confirmed";

  return (
    <div className="max-w-xl space-y-4">
      <Link href="/dashboard/bookings" className="text-sm text-blue-700 hover:underline">
        ← Back to bookings
      </Link>

      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">Booking #{booking.id}</h1>
        <BookingStatusBadge status={booking.status} />
      </div>

      <dl className="divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white">
        <Row label="Customer">
          <span>Customer #{booking.customer_id}</span>
          <span className="block text-xs text-slate-400">
            Name unavailable — no customer lookup endpoint exists yet
          </span>
        </Row>
        <Row label="Service">{serviceName}</Row>
        <Row label="Staff">{staffName}</Row>
        <Row label="Starts">{formatInBusinessTimezone(booking.starts_at, context.business.timezone)}</Row>
        <Row label="Ends">{formatInBusinessTimezone(booking.ends_at, context.business.timezone)}</Row>
        <Row label="Timezone">{context.business.timezone}</Row>
        <Row label="Source">{booking.source}</Row>
        {booking.cancel_reason ? <Row label="Cancel reason">{booking.cancel_reason}</Row> : null}
      </dl>

      {canModify ? (
        <div className="flex gap-3">
          <RescheduleBookingDialog
            bookingId={booking.id}
            serviceId={booking.service_id}
            staffId={booking.staff_id}
            timezone={context.business.timezone}
          />
          <CancelBookingDialog bookingId={booking.id} />
        </div>
      ) : null}
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-3 gap-4 px-4 py-3 text-sm">
      <dt className="text-slate-500">{label}</dt>
      <dd className="col-span-2 text-slate-900">{children}</dd>
    </div>
  );
}
