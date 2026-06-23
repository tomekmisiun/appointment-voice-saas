"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { clientFetch } from "@/lib/api/client";
import type { AvailabilitySlot, BookingRead } from "@/lib/api/types";
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

export interface AvailabilityParams {
  serviceId: number;
  staffId: number | null;
  date: string;
}

function buildAvailabilityQuery(params: AvailabilityParams): string {
  const search = new URLSearchParams({
    service_id: String(params.serviceId),
    date: params.date,
  });
  if (params.staffId !== null) {
    search.set("staff_id", String(params.staffId));
  }
  return search.toString();
}

/**
 * `enabled` must gate this on the reschedule dialog actually being open —
 * it must not fetch the moment the detail page mounts, both to avoid a
 * wasted request on every eligible page view and because availability
 * fetched before the dialog opens can go stale by the time the admin
 * actually picks a slot. `staleTime: 0` means re-opening always refetches
 * fresh, overriding the app-wide default in components/providers/QueryProvider.
 */
export function useAvailabilityQuery(params: AvailabilityParams, enabled: boolean) {
  return useQuery({
    queryKey: ["availability", params] as const,
    queryFn: () => clientFetch<AvailabilitySlot[]>(`/api/availability?${buildAvailabilityQuery(params)}`),
    enabled,
    staleTime: 0,
  });
}

export function useRescheduleBookingMutation(bookingId: number) {
  return useMutation({
    mutationFn: ({ newStartsAt, reason }: { newStartsAt: string; reason: string | undefined }) =>
      clientFetch<BookingRead>(`/api/bookings/${bookingId}/reschedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_starts_at: newStartsAt, reason }),
      }),
  });
}
