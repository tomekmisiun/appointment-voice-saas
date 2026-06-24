import Link from "next/link";
import { redirect } from "next/navigation";
import { AddStaffDialog } from "@/features/staff/components/AddStaffDialog";
import { EditStaffDialog } from "@/features/staff/components/EditStaffDialog";
import { ToggleStaffActiveButton } from "@/features/staff/components/ToggleStaffActiveButton";
import { getCurrentBusinessContextOrRefresh } from "@/features/dashboard/current-business";
import { ApiError } from "@/lib/api/errors";
import { fetchFromBackend } from "@/lib/api/server";
import type { StaffRead } from "@/lib/api/types";
import { roleIncludes } from "@/lib/auth/roles";
import { getSession } from "@/lib/auth/server";

const PAGE_SIZE = 20;

/** Falls back to page 1 for anything that isn't a real positive integer (e.g. "1.5", "Infinity", "-3", garbage) — never forwards a value FastAPI's int query param would 422 on. */
function parsePage(raw: string | undefined): number {
  const parsed = Number(raw);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}

export default async function StaffPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; includeInactive?: string }>;
}) {
  const params = await searchParams;
  const session = await getSession();
  if (!session) {
    redirect("/login");
  }

  const context = await getCurrentBusinessContextOrRefresh(session.accessToken, "/dashboard/staff");
  if (context.kind !== "single") {
    return null;
  }

  const page = parsePage(params.page);
  const includeInactive = params.includeInactive === "true";
  const canManage = roleIncludes(context.user.role, "admin");

  let staff: StaffRead[];
  try {
    staff = await fetchFromBackend<StaffRead[]>(
      `/api/v1/businesses/${context.business.id}/staff?page=${page}&size=${PAGE_SIZE}&include_inactive=${includeInactive}`,
      session.accessToken,
    );
  } catch (error) {
    if (error instanceof ApiError && error.isAuthError) {
      redirect("/auth/refresh?next=/dashboard/staff");
    }
    throw error;
  }

  return (
    <div className="max-w-3xl space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">Staff</h1>
        {canManage ? <AddStaffDialog /> : null}
      </div>

      <Link
        href={`/dashboard/staff?page=1&includeInactive=${includeInactive ? "false" : "true"}`}
        className="text-sm text-blue-700 hover:underline"
      >
        {includeInactive ? "Hide inactive staff" : "Show inactive staff"}
      </Link>

      {staff.length === 0 ? (
        <p className="text-sm text-slate-500">No staff configured yet.</p>
      ) : (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-xs uppercase text-slate-500">
              <th scope="col" className="py-2 pr-4">
                Name
              </th>
              <th scope="col" className="py-2 pr-4">
                Phone
              </th>
              <th scope="col" className="py-2 pr-4">
                Status
              </th>
              {canManage ? (
                <th scope="col" className="py-2 pr-4">
                  Actions
                </th>
              ) : null}
            </tr>
          </thead>
          <tbody>
            {staff.map((member) => (
              <tr key={member.id} className="border-b border-slate-100">
                <td className="py-2 pr-4">{member.name}</td>
                <td className="py-2 pr-4">{member.phone || "—"}</td>
                <td className="py-2 pr-4">
                  {member.is_active ? (
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
                      <EditStaffDialog staff={member} />
                      <ToggleStaffActiveButton staffId={member.id} isActive={member.is_active} />
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
          href={`/dashboard/staff?page=${Math.max(1, page - 1)}&includeInactive=${includeInactive}`}
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
          href={`/dashboard/staff?page=${page + 1}&includeInactive=${includeInactive}`}
          aria-disabled={staff.length < PAGE_SIZE}
          className={`rounded-md border px-3 py-1 text-sm ${
            staff.length < PAGE_SIZE
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
