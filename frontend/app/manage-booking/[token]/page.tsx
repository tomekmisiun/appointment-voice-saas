import { notFound } from "next/navigation";
import { ManageBookingClient } from "./ManageBookingClient";
import { fetchFromBackendPublic } from "@/lib/api/server";
import { ApiError } from "@/lib/api/errors";
import type { BookingPublicRead } from "@/lib/api/types";

export default async function ManageBookingPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;

  let booking: BookingPublicRead;
  try {
    booking = await fetchFromBackendPublic<BookingPublicRead>(
      `/api/v1/bookings/public/${encodeURIComponent(token)}`,
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  return (
    <main className="mx-auto max-w-lg px-4 py-12">
      <h1 className="text-2xl font-bold text-slate-900">Manage your booking</h1>
      <p className="mt-2 text-sm text-slate-500">Booking #{booking.id}</p>
      <div className="mt-6 rounded-lg border border-slate-200 p-6">
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-slate-500">Status</dt>
            <dd className="font-medium capitalize text-slate-900">{booking.status}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-500">Starts at</dt>
            <dd className="font-medium text-slate-900">
              {new Date(booking.starts_at).toLocaleString()}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-slate-500">Ends at</dt>
            <dd className="font-medium text-slate-900">
              {new Date(booking.ends_at).toLocaleString()}
            </dd>
          </div>
        </dl>
      </div>
      <ManageBookingClient token={token} booking={booking} />
    </main>
  );
}
