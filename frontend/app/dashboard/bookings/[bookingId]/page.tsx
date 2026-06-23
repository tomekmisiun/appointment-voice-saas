import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { BookingStatusBadge } from "@/features/bookings/components/BookingStatusBadge";
import { resolveNameOrFallback } from "@/features/bookings/server";
import { formatInBusinessTimezone } from "@/features/bookings/utils";
import { getCurrentBusinessContext } from "@/features/dashboard/current-business";
import { ApiError } from "@/lib/api/errors";
import { fetchFromBackend } from "@/lib/api/server";
import type { BookingRead } from "@/lib/api/types";
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
