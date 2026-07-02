"use server";

import { getBackendApiUrl } from "@/lib/api/config";
import { ApiError, parseErrorBody } from "@/lib/api/errors";
import type { BookingPublicRead } from "@/lib/api/types";

export interface ManageBookingResult {
  ok: boolean;
  booking?: BookingPublicRead;
  error?: string;
}

async function postPublic<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${getBackendApiUrl()}${path}`, {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const err = await parseErrorBody(response);
    throw new ApiError(response.status, err);
  }

  return (await response.json()) as T;
}

export async function cancelPublicBookingAction(
  token: string,
): Promise<ManageBookingResult> {
  try {
    const booking = await postPublic<BookingPublicRead>(
      `/api/v1/bookings/public/${encodeURIComponent(token)}/cancel`,
      { reason: "Customer cancelled via link" },
    );
    return { ok: true, booking };
  } catch (error) {
    if (error instanceof ApiError) {
      return { ok: false, error: error.message };
    }
    throw error;
  }
}

export async function reschedulePublicBookingAction(
  token: string,
  newStartsAt: string,
): Promise<ManageBookingResult> {
  try {
    const booking = await postPublic<BookingPublicRead>(
      `/api/v1/bookings/public/${encodeURIComponent(token)}/reschedule`,
      { new_starts_at: newStartsAt, reason: "Customer rescheduled via link" },
    );
    return { ok: true, booking };
  } catch (error) {
    if (error instanceof ApiError) {
      return { ok: false, error: error.message };
    }
    throw error;
  }
}
