import Link from "next/link";
import { redirect } from "next/navigation";
import { AddServiceDialog } from "@/features/services/components/AddServiceDialog";
import { EditServiceDialog } from "@/features/services/components/EditServiceDialog";
import { ToggleServiceActiveButton } from "@/features/services/components/ToggleServiceActiveButton";
import { getCurrentBusinessContextOrRefresh } from "@/features/dashboard/current-business";
import { ApiError } from "@/lib/api/errors";
import { fetchFromBackend } from "@/lib/api/server";
import type { ServiceRead } from "@/lib/api/types";
import { getSession } from "@/lib/auth/server";

const PAGE_SIZE = 20;

function parsePage(raw: string | undefined): number {
  const parsed = Number(raw);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}

function formatPrice(minorUnits: number | null | undefined, currency: string | null | undefined): string {
  if (minorUnits == null || currency == null) return "—";
  return `${(minorUnits / 100).toFixed(2)} ${currency}`;
}

export default async function ServicesPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; includeInactive?: string }>;
}) {
  const params = await searchParams;
  const session = await getSession();
  if (!session) redirect("/login");

  const context = await getCurrentBusinessContextOrRefresh(session.accessToken, "/dashboard/services");
  if (context.kind !== "single") return null;

  const page = parsePage(params.page);
  const includeInactive = params.includeInactive === "true";
  const canManage = true;

  let services: ServiceRead[];
  try {
    services = await fetchFromBackend<ServiceRead[]>(
      `/api/v1/businesses/${context.business.id}/services?page=${page}&size=${PAGE_SIZE}&include_inactive=${includeInactive}`,
      session.accessToken,
    );
  } catch (error) {
    if (error instanceof ApiError && error.isAuthError) {
      redirect("/auth/refresh?next=/dashboard/services");
    }
    throw error;
  }

  return (
    <div className="max-w-3xl space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">Services</h1>
        {canManage ? <AddServiceDialog /> : null}
      </div>

      <Link
        href={`/dashboard/services?page=1&includeInactive=${includeInactive ? "false" : "true"}`}
        className="text-sm text-blue-700 hover:underline"
      >
        {includeInactive ? "Hide inactive services" : "Show inactive services"}
      </Link>

      {services.length === 0 ? (
        <p className="text-sm text-slate-500">No services configured yet.</p>
      ) : (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-xs uppercase text-slate-500">
              <th scope="col" className="py-2 pr-4">Name</th>
              <th scope="col" className="py-2 pr-4">Duration</th>
              <th scope="col" className="py-2 pr-4">Price</th>
              <th scope="col" className="py-2 pr-4">Status</th>
              {canManage ? <th scope="col" className="py-2 pr-4">Actions</th> : null}
            </tr>
          </thead>
          <tbody>
            {services.map((svc) => (
              <tr key={svc.id} className="border-b border-slate-100">
                <td className="py-2 pr-4 font-medium">{svc.name}</td>
                <td className="py-2 pr-4">{svc.duration_minutes} min</td>
                <td className="py-2 pr-4">{formatPrice(svc.price_minor_units, svc.currency)}</td>
                <td className="py-2 pr-4">
                  {svc.is_active ? (
                    <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">
                      Active
                    </span>
                  ) : (
                    <span className="rounded bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-600">
                      Inactive
                    </span>
                  )}
                </td>
                {canManage ? (
                  <td className="py-2 pr-4">
                    <div className="flex gap-2">
                      <EditServiceDialog service={svc} />
                      <ToggleServiceActiveButton serviceId={svc.id} isActive={svc.is_active} />
                    </div>
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="flex items-center gap-3">
        <Link
          href={`/dashboard/services?page=${Math.max(1, page - 1)}&includeInactive=${includeInactive}`}
          aria-disabled={page === 1}
          className={`rounded-md border px-3 py-1 text-sm ${
            page === 1
              ? "pointer-events-none border-slate-200 text-slate-400"
              : "border-slate-300 text-slate-700 hover:bg-slate-50"
          }`}
        >
          Previous
        </Link>
        <span className="text-sm text-slate-500">Page {page}</span>
        <Link
          href={`/dashboard/services?page=${page + 1}&includeInactive=${includeInactive}`}
          aria-disabled={services.length < PAGE_SIZE}
          className={`rounded-md border px-3 py-1 text-sm ${
            services.length < PAGE_SIZE
              ? "pointer-events-none border-slate-200 text-slate-400"
              : "border-slate-300 text-slate-700 hover:bg-slate-50"
          }`}
        >
          Next
        </Link>
      </div>
    </div>
  );
}
