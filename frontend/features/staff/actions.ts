"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { getCurrentBusinessContext } from "@/features/dashboard/current-business";
import { ApiError } from "@/lib/api/errors";
import { fetchFromBackend } from "@/lib/api/server";
import type { StaffCreate, StaffRead, StaffUpdate } from "@/lib/api/types";
import { roleIncludes } from "@/lib/auth/roles";
import { getSession, isAccessTokenExpired } from "@/lib/auth/server";
import { staffFormSchema } from "./schemas";

export interface StaffActionResult {
  ok: boolean;
  error?: string;
}

/**
 * Server Actions, not a Route Handler + client fetch: staff management is
 * a small admin CRUD screen, not interactive customer-facing data, so
 * there's no need for React Query's client-side cache — a plain form
 * submission + revalidatePath() is simpler and just as correct. Next.js
 * Server Actions get built-in Origin validation from the framework
 * itself, so this doesn't need the custom CSRF wrapper Route Handlers do.
 *
 * Session expiry is handled the same way Server Components handle it —
 * redirect through /auth/refresh — rather than returning a raw ApiError
 * to the caller, which would otherwise surface as an unhandled-exception
 * error boundary instead of a clean refresh-and-retry.
 */
async function resolveAdminBusinessContext() {
  const session = await getSession();
  if (!session) {
    redirect("/login");
  }

  if (isAccessTokenExpired(session)) {
    redirect("/auth/refresh?next=/dashboard/staff");
  }

  let context;
  try {
    context = await getCurrentBusinessContext(session.accessToken);
  } catch (error) {
    if (error instanceof ApiError && error.isAuthError) {
      redirect("/auth/refresh?next=/dashboard/staff");
    }
    throw error;
  }

  if (context.kind !== "single") {
    return { error: "No single active business is available for this account." } as const;
  }

  if (!roleIncludes(context.user.role, "admin")) {
    return { error: "Only an admin can manage staff." } as const;
  }

  return { session, businessId: context.business.id } as const;
}

/**
 * Shared catch-block handling for the mutation calls below: there's a real
 * (if narrow) window where the token looks valid when
 * resolveAdminBusinessContext() checks it but is revoked or expires by the
 * time the actual POST/PATCH lands — without this, that 401 would render
 * inline as if it were a normal validation error instead of sending the
 * user through the same refresh flow every other auth failure here uses.
 */
function toStaffActionResult(error: unknown): StaffActionResult {
  if (error instanceof ApiError) {
    if (error.isAuthError) {
      redirect("/auth/refresh?next=/dashboard/staff");
    }
    return { ok: false, error: error.message };
  }
  throw error;
}

export async function createStaffAction(
  _previous: StaffActionResult,
  formData: FormData,
): Promise<StaffActionResult> {
  const parsed = staffFormSchema.safeParse({
    name: formData.get("name"),
    phone: formData.get("phone"),
  });
  if (!parsed.success) {
    return { ok: false, error: parsed.error.issues[0]?.message ?? "Invalid input." };
  }

  const resolved = await resolveAdminBusinessContext();
  if ("error" in resolved) {
    return { ok: false, error: resolved.error };
  }

  const body: StaffCreate = { name: parsed.data.name, phone: parsed.data.phone };

  try {
    await fetchFromBackend<StaffRead>(`/api/v1/businesses/${resolved.businessId}/staff`, resolved.session.accessToken, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (error) {
    return toStaffActionResult(error);
  }

  revalidatePath("/dashboard/staff");
  return { ok: true };
}

export async function updateStaffAction(
  staffId: number,
  _previous: StaffActionResult,
  formData: FormData,
): Promise<StaffActionResult> {
  const parsed = staffFormSchema.safeParse({
    name: formData.get("name"),
    phone: formData.get("phone"),
  });
  if (!parsed.success) {
    return { ok: false, error: parsed.error.issues[0]?.message ?? "Invalid input." };
  }

  const resolved = await resolveAdminBusinessContext();
  if ("error" in resolved) {
    return { ok: false, error: resolved.error };
  }

  // phone is always a string here ("" for blank) — see schemas.ts: the
  // backend's update_staff only assigns phone when it's not None, so
  // sending null/omitting it can never clear an existing value, but an
  // empty string is "not None" and does clear it through this same
  // contract without needing a backend change.
  const body: StaffUpdate = { name: parsed.data.name, phone: parsed.data.phone };

  try {
    await fetchFromBackend<StaffRead>(
      `/api/v1/businesses/${resolved.businessId}/staff/${staffId}`,
      resolved.session.accessToken,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    );
  } catch (error) {
    return toStaffActionResult(error);
  }

  revalidatePath("/dashboard/staff");
  return { ok: true };
}

export async function setStaffActiveAction(staffId: number, isActive: boolean): Promise<StaffActionResult> {
  const resolved = await resolveAdminBusinessContext();
  if ("error" in resolved) {
    return { ok: false, error: resolved.error };
  }

  const body: StaffUpdate = { is_active: isActive };

  try {
    await fetchFromBackend<StaffRead>(
      `/api/v1/businesses/${resolved.businessId}/staff/${staffId}`,
      resolved.session.accessToken,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    );
  } catch (error) {
    return toStaffActionResult(error);
  }

  revalidatePath("/dashboard/staff");
  return { ok: true };
}
