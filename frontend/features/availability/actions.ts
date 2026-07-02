"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { getCurrentBusinessContext } from "@/features/dashboard/current-business";
import { ApiError } from "@/lib/api/errors";
import { fetchFromBackend } from "@/lib/api/server";
import type {
  AvailabilityExceptionCreate,
  AvailabilityExceptionRead,
  RecurringStaffBlockCreate,
  RecurringStaffBlockRead,
  WorkingHoursCreate,
  WorkingHoursRead,
} from "@/lib/api/types";
import { getSession, isAccessTokenExpired } from "@/lib/auth/server";

export interface AvailabilityActionResult {
  ok: boolean;
  error?: string;
}

async function resolveAdminBusinessContext() {
  const session = await getSession();
  if (!session) redirect("/login");
  if (isAccessTokenExpired(session)) redirect("/auth/refresh?next=/dashboard/availability");

  let context;
  try {
    context = await getCurrentBusinessContext(session.accessToken);
  } catch (error) {
    if (error instanceof ApiError && error.isAuthError) {
      redirect("/auth/refresh?next=/dashboard/availability");
    }
    throw error;
  }

  if (context.kind !== "single") {
    return { error: "No single active business is available for this account." } as const;
  }

  return { session, businessId: context.business.id } as const;
}

function toResult(error: unknown): AvailabilityActionResult {
  if (error instanceof ApiError) {
    if (error.isAuthError) redirect("/auth/refresh?next=/dashboard/availability");
    return { ok: false, error: error.message };
  }
  throw error;
}

// ── Working hours ──────────────────────────────────────────────────────────────

export async function createWorkingHoursAction(
  _previous: AvailabilityActionResult,
  formData: FormData,
): Promise<AvailabilityActionResult> {
  const dayRaw = formData.get("day_of_week");
  const startTime = formData.get("start_time");
  const endTime = formData.get("end_time");

  if (!dayRaw || !startTime || !endTime) {
    return { ok: false, error: "Day, start time and end time are required." };
  }
  const day = Number(dayRaw);
  if (!Number.isInteger(day) || day < 0 || day > 6) {
    return { ok: false, error: "Invalid day of week." };
  }

  const resolved = await resolveAdminBusinessContext();
  if ("error" in resolved) return { ok: false, error: resolved.error };

  const body: WorkingHoursCreate = {
    day_of_week: day,
    start_time: String(startTime),
    end_time: String(endTime),
    staff_id: null,
  };

  try {
    await fetchFromBackend<WorkingHoursRead>(
      `/api/v1/businesses/${resolved.businessId}/working-hours`,
      resolved.session.accessToken,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) },
    );
  } catch (error) {
    return toResult(error);
  }

  revalidatePath("/dashboard/availability");
  return { ok: true };
}

export async function deleteWorkingHoursAction(whId: number): Promise<AvailabilityActionResult> {
  const resolved = await resolveAdminBusinessContext();
  if ("error" in resolved) return { ok: false, error: resolved.error };

  try {
    await fetchFromBackend<void>(
      `/api/v1/businesses/${resolved.businessId}/working-hours/${whId}`,
      resolved.session.accessToken,
      { method: "DELETE" },
    );
  } catch (error) {
    return toResult(error);
  }

  revalidatePath("/dashboard/availability");
  return { ok: true };
}

// ── Recurring staff blocks ─────────────────────────────────────────────────────

export async function createRecurringBlockAction(
  _previous: AvailabilityActionResult,
  formData: FormData,
): Promise<AvailabilityActionResult> {
  const dayRaw = formData.get("day_of_week");
  const startTime = formData.get("start_time");
  const endTime = formData.get("end_time");
  const reason = formData.get("reason");

  if (!dayRaw || !startTime || !endTime) {
    return { ok: false, error: "Day, start time and end time are required." };
  }
  const day = Number(dayRaw);
  if (!Number.isInteger(day) || day < 0 || day > 6) {
    return { ok: false, error: "Invalid day of week." };
  }

  const resolved = await resolveAdminBusinessContext();
  if ("error" in resolved) return { ok: false, error: resolved.error };

  const body: RecurringStaffBlockCreate = {
    day_of_week: day,
    start_time: String(startTime),
    end_time: String(endTime),
    reason: reason ? String(reason) : null,
    staff_id: null,
  };

  try {
    await fetchFromBackend<RecurringStaffBlockRead>(
      `/api/v1/businesses/${resolved.businessId}/recurring-staff-blocks`,
      resolved.session.accessToken,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) },
    );
  } catch (error) {
    return toResult(error);
  }

  revalidatePath("/dashboard/availability");
  return { ok: true };
}

export async function deleteRecurringBlockAction(blockId: number): Promise<AvailabilityActionResult> {
  const resolved = await resolveAdminBusinessContext();
  if ("error" in resolved) return { ok: false, error: resolved.error };

  try {
    await fetchFromBackend<void>(
      `/api/v1/businesses/${resolved.businessId}/recurring-staff-blocks/${blockId}`,
      resolved.session.accessToken,
      { method: "DELETE" },
    );
  } catch (error) {
    return toResult(error);
  }

  revalidatePath("/dashboard/availability");
  return { ok: true };
}

// ── Availability exceptions ───────────────────────────────────────────────────

export async function createExceptionAction(
  _previous: AvailabilityActionResult,
  formData: FormData,
): Promise<AvailabilityActionResult> {
  const date = formData.get("date");
  const isClosed = formData.get("is_closed") === "true";
  const startTime = formData.get("start_time");
  const endTime = formData.get("end_time");
  const reason = formData.get("reason");

  if (!date) return { ok: false, error: "Date is required." };
  if (!isClosed && (!startTime || !endTime)) {
    return { ok: false, error: "Start and end time are required when not fully closed." };
  }

  const resolved = await resolveAdminBusinessContext();
  if ("error" in resolved) return { ok: false, error: resolved.error };

  const body: AvailabilityExceptionCreate = {
    date: String(date),
    is_closed: isClosed,
    start_time: isClosed ? null : String(startTime),
    end_time: isClosed ? null : String(endTime),
    reason: reason ? String(reason) : null,
    staff_id: null,
  };

  try {
    await fetchFromBackend<AvailabilityExceptionRead>(
      `/api/v1/businesses/${resolved.businessId}/availability-exceptions`,
      resolved.session.accessToken,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) },
    );
  } catch (error) {
    return toResult(error);
  }

  revalidatePath("/dashboard/availability");
  return { ok: true };
}

export async function deleteExceptionAction(exceptionId: number): Promise<AvailabilityActionResult> {
  const resolved = await resolveAdminBusinessContext();
  if ("error" in resolved) return { ok: false, error: resolved.error };

  try {
    await fetchFromBackend<void>(
      `/api/v1/businesses/${resolved.businessId}/availability-exceptions/${exceptionId}`,
      resolved.session.accessToken,
      { method: "DELETE" },
    );
  } catch (error) {
    return toResult(error);
  }

  revalidatePath("/dashboard/availability");
  return { ok: true };
}
