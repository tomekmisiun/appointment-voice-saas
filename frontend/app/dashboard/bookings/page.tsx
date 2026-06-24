import { redirect } from "next/navigation";
import { BookingsListClient } from "@/features/bookings/components/BookingsListClient";
import { getCurrentBusinessContextOrRefresh } from "@/features/dashboard/current-business";
import { fetchFromBackend } from "@/lib/api/server";
import type { ServiceRead, StaffRead } from "@/lib/api/types";
import { getSession } from "@/lib/auth/server";

export default async function BookingsListPage() {
  const session = await getSession();
  if (!session) {
    redirect("/login");
  }

  // Memoized via React's cache() — already resolved once by the layout
  // above for the same access token, so this isn't a second network call.
  const context = await getCurrentBusinessContextOrRefresh(session.accessToken, "/dashboard/bookings");
  if (context.kind !== "single") {
    return null;
  }

  // Fetched here, server-side, once per page load — not per row, and not
  // re-fetched on every filter/pagination change (those only refetch the
  // bookings list itself, client-side). Staff/service lists are small,
  // bounded reference data for the current business.
  const [staff, services] = await Promise.all([
    fetchFromBackend<StaffRead[]>(
      `/api/v1/businesses/${context.business.id}/staff?size=100`,
      session.accessToken,
    ),
    fetchFromBackend<ServiceRead[]>(
      `/api/v1/businesses/${context.business.id}/services?size=100`,
      session.accessToken,
    ),
  ]);

  return <BookingsListClient business={context.business} staff={staff} services={services} />;
}
