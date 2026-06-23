"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { clientFetch } from "@/lib/api/client";
import type { BookingRead } from "@/lib/api/types";
import type { BookingsFilters } from "./types";

function buildQuery(filters: BookingsFilters): string {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.staffId !== undefined) params.set("staff_id", String(filters.staffId));
  params.set("page", String(filters.page));
  params.set("size", String(filters.size));
  return params.toString();
}

export function bookingsQueryKey(filters: BookingsFilters) {
  return ["bookings", filters] as const;
}

export function useBookingsQuery(filters: BookingsFilters) {
  return useQuery({
    queryKey: bookingsQueryKey(filters),
    queryFn: () => clientFetch<BookingRead[]>(`/api/bookings?${buildQuery(filters)}`),
    placeholderData: (previousData) => previousData,
  });
}

export function useCancelBookingMutation(bookingId: number) {
  return useMutation({
    mutationFn: (reason: string | undefined) =>
      clientFetch<BookingRead>(`/api/bookings/${bookingId}/cancel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      }),
  });
}
