import "server-only";
import { fetchFromBackend } from "@/lib/api/server";
import type { ServiceRead, StaffRead, WorkingHoursRead } from "@/lib/api/types";

const DEFAULT_LIST_PAGE_SIZE = 20;

export interface SetupStatusItem {
  label: string;
  /** Exact when below the default page size; otherwise a floor, not a real total. */
  count: number;
  countIsFloor: boolean;
  configured: boolean;
}

export interface SetupStatus {
  staff: SetupStatusItem;
  services: SetupStatusItem;
  workingHours: SetupStatusItem;
}

function toStatusItem(label: string, items: unknown[]): SetupStatusItem {
  return {
    label,
    count: items.length,
    countIsFloor: items.length === DEFAULT_LIST_PAGE_SIZE,
    configured: items.length > 0,
  };
}

/**
 * Real setup-status checks for the dashboard overview — deliberately not
 * booking counts or any other metric (the backend has no owner-metrics
 * endpoint yet, see P2-013 in docs/frontend/frontend-roadmap.md). Each
 * count comes from the first page of the real list endpoint; when it hits
 * the default page size it's reported as a floor ("20+"), not asserted as
 * an exact total.
 */
export async function getSetupStatus(accessToken: string, businessId: number): Promise<SetupStatus> {
  const [staff, services, workingHours] = await Promise.all([
    fetchFromBackend<StaffRead[]>(`/api/v1/businesses/${businessId}/staff`, accessToken),
    fetchFromBackend<ServiceRead[]>(`/api/v1/businesses/${businessId}/services`, accessToken),
    fetchFromBackend<WorkingHoursRead[]>(`/api/v1/businesses/${businessId}/working-hours`, accessToken),
  ]);

  return {
    staff: toStatusItem("Staff", staff),
    services: toStatusItem("Services", services),
    workingHours: toStatusItem("Working hours", workingHours),
  };
}
