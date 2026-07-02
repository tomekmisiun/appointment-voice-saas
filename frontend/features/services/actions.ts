"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { getCurrentBusinessContext } from "@/features/dashboard/current-business";
import { ApiError } from "@/lib/api/errors";
import { fetchFromBackend } from "@/lib/api/server";
import type { ServiceCreate, ServiceRead, ServiceUpdate } from "@/lib/api/types";
import { getSession, isAccessTokenExpired } from "@/lib/auth/server";
import { serviceFormSchema } from "./schemas";

export interface ServiceActionResult {
  ok: boolean;
  error?: string;
}

async function resolveAdminBusinessContext() {
  const session = await getSession();
  if (!session) redirect("/login");
  if (isAccessTokenExpired(session)) redirect("/auth/refresh?next=/dashboard/services");

  let context;
  try {
    context = await getCurrentBusinessContext(session.accessToken);
  } catch (error) {
    if (error instanceof ApiError && error.isAuthError) {
      redirect("/auth/refresh?next=/dashboard/services");
    }
    throw error;
  }

  if (context.kind !== "single") {
    return { error: "No single active business is available for this account." } as const;
  }

  return { session, businessId: context.business.id } as const;
}

function toServiceActionResult(error: unknown): ServiceActionResult {
  if (error instanceof ApiError) {
    if (error.isAuthError) redirect("/auth/refresh?next=/dashboard/services");
    return { ok: false, error: error.message };
  }
  throw error;
}

export async function createServiceAction(
  _previous: ServiceActionResult,
  formData: FormData,
): Promise<ServiceActionResult> {
  const raw = {
    name: formData.get("name"),
    duration_minutes: formData.get("duration_minutes"),
    price_minor_units: formData.get("price_minor_units") || undefined,
    currency: formData.get("currency") || undefined,
  };
  const parsed = serviceFormSchema.safeParse(raw);
  if (!parsed.success) {
    return { ok: false, error: parsed.error.issues[0]?.message ?? "Invalid input." };
  }

  const resolved = await resolveAdminBusinessContext();
  if ("error" in resolved) return { ok: false, error: resolved.error };

  const body: ServiceCreate = {
    name: parsed.data.name,
    duration_minutes: parsed.data.duration_minutes,
    deposit_required: false,
    price_minor_units:
      parsed.data.price_minor_units !== "" && parsed.data.price_minor_units !== undefined
        ? Number(parsed.data.price_minor_units)
        : undefined,
    currency:
      parsed.data.currency !== "" && parsed.data.currency !== undefined
        ? parsed.data.currency
        : undefined,
  };

  try {
    await fetchFromBackend<ServiceRead>(
      `/api/v1/businesses/${resolved.businessId}/services`,
      resolved.session.accessToken,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) },
    );
  } catch (error) {
    return toServiceActionResult(error);
  }

  revalidatePath("/dashboard/services");
  return { ok: true };
}

export async function updateServiceAction(
  serviceId: number,
  _previous: ServiceActionResult,
  formData: FormData,
): Promise<ServiceActionResult> {
  const raw = {
    name: formData.get("name"),
    duration_minutes: formData.get("duration_minutes"),
    price_minor_units: formData.get("price_minor_units") || undefined,
    currency: formData.get("currency") || undefined,
  };
  const parsed = serviceFormSchema.safeParse(raw);
  if (!parsed.success) {
    return { ok: false, error: parsed.error.issues[0]?.message ?? "Invalid input." };
  }

  const resolved = await resolveAdminBusinessContext();
  if ("error" in resolved) return { ok: false, error: resolved.error };

  const body: ServiceUpdate = {
    name: parsed.data.name,
    duration_minutes: parsed.data.duration_minutes,
    price_minor_units:
      parsed.data.price_minor_units !== "" && parsed.data.price_minor_units !== undefined
        ? Number(parsed.data.price_minor_units)
        : null,
    currency:
      parsed.data.currency !== "" && parsed.data.currency !== undefined
        ? parsed.data.currency
        : null,
  };

  try {
    await fetchFromBackend<ServiceRead>(
      `/api/v1/businesses/${resolved.businessId}/services/${serviceId}`,
      resolved.session.accessToken,
      { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) },
    );
  } catch (error) {
    return toServiceActionResult(error);
  }

  revalidatePath("/dashboard/services");
  return { ok: true };
}

export async function setServiceActiveAction(
  serviceId: number,
  isActive: boolean,
): Promise<ServiceActionResult> {
  const resolved = await resolveAdminBusinessContext();
  if ("error" in resolved) return { ok: false, error: resolved.error };

  try {
    await fetchFromBackend<ServiceRead>(
      `/api/v1/businesses/${resolved.businessId}/services/${serviceId}`,
      resolved.session.accessToken,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: isActive } satisfies ServiceUpdate),
      },
    );
  } catch (error) {
    return toServiceActionResult(error);
  }

  revalidatePath("/dashboard/services");
  return { ok: true };
}
