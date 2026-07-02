import { redirect } from "next/navigation";
import { AddExceptionDialog } from "@/features/availability/components/AddExceptionDialog";
import { AddRecurringBlockDialog } from "@/features/availability/components/AddRecurringBlockDialog";
import { AddWorkingHoursDialog } from "@/features/availability/components/AddWorkingHoursDialog";
import { DeleteButton } from "@/features/availability/components/DeleteButton";
import {
  deleteExceptionAction,
  deleteRecurringBlockAction,
  deleteWorkingHoursAction,
} from "@/features/availability/actions";
import { getCurrentBusinessContextOrRefresh } from "@/features/dashboard/current-business";
import { ApiError } from "@/lib/api/errors";
import { fetchFromBackend } from "@/lib/api/server";
import type {
  AvailabilityExceptionRead,
  RecurringStaffBlockRead,
  WorkingHoursRead,
} from "@/lib/api/types";
import { getSession } from "@/lib/auth/server";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default async function AvailabilityPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const context = await getCurrentBusinessContextOrRefresh(
    session.accessToken,
    "/dashboard/availability",
  );
  if (context.kind !== "single") return null;

  const canManage = true;
  const bizId = context.business.id;

  let workingHours: WorkingHoursRead[] = [];
  let blocks: RecurringStaffBlockRead[] = [];
  let exceptions: AvailabilityExceptionRead[] = [];

  try {
    [workingHours, blocks, exceptions] = await Promise.all([
      fetchFromBackend<WorkingHoursRead[]>(
        `/api/v1/businesses/${bizId}/working-hours`,
        session.accessToken,
      ),
      fetchFromBackend<RecurringStaffBlockRead[]>(
        `/api/v1/businesses/${bizId}/recurring-staff-blocks`,
        session.accessToken,
      ),
      fetchFromBackend<AvailabilityExceptionRead[]>(
        `/api/v1/businesses/${bizId}/availability-exceptions`,
        session.accessToken,
      ),
    ]);
  } catch (error) {
    if (error instanceof ApiError && error.isAuthError) {
      redirect("/auth/refresh?next=/dashboard/availability");
    }
    throw error;
  }

  return (
    <div className="max-w-3xl space-y-10">
      {/* Working hours */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold text-slate-900">Working hours</h1>
          {canManage ? <AddWorkingHoursDialog /> : null}
        </div>
        <p className="text-sm text-slate-500">
          Recurring weekly hours when the business accepts bookings (business-wide). Set
          staff-specific hours through the Staff page.
        </p>
        {workingHours.length === 0 ? (
          <p className="text-sm text-slate-500">No working hours configured yet.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs uppercase text-slate-500">
                <th scope="col" className="py-2 pr-4">Day</th>
                <th scope="col" className="py-2 pr-4">Start</th>
                <th scope="col" className="py-2 pr-4">End</th>
                <th scope="col" className="py-2 pr-4">Scope</th>
                {canManage ? <th scope="col" className="py-2 pr-4">Actions</th> : null}
              </tr>
            </thead>
            <tbody>
              {workingHours.map((wh) => (
                <tr key={wh.id} className="border-b border-slate-100">
                  <td className="py-2 pr-4">{DAYS[wh.day_of_week]}</td>
                  <td className="py-2 pr-4">{wh.start_time}</td>
                  <td className="py-2 pr-4">{wh.end_time}</td>
                  <td className="py-2 pr-4 text-xs text-slate-500">
                    {wh.staff_id != null ? `Staff #${wh.staff_id}` : "Business-wide"}
                  </td>
                  {canManage ? (
                    <td className="py-2 pr-4">
                      <DeleteButton action={deleteWorkingHoursAction.bind(null, wh.id)} />
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Recurring blocks */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Recurring unavailable blocks</h2>
          {canManage ? <AddRecurringBlockDialog /> : null}
        </div>
        <p className="text-sm text-slate-500">
          Weekly windows subtracted from availability every matching weekday (e.g. lunch breaks).
        </p>
        {blocks.length === 0 ? (
          <p className="text-sm text-slate-500">No recurring blocks configured.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs uppercase text-slate-500">
                <th scope="col" className="py-2 pr-4">Day</th>
                <th scope="col" className="py-2 pr-4">Start</th>
                <th scope="col" className="py-2 pr-4">End</th>
                <th scope="col" className="py-2 pr-4">Reason</th>
                {canManage ? <th scope="col" className="py-2 pr-4">Actions</th> : null}
              </tr>
            </thead>
            <tbody>
              {blocks.map((b) => (
                <tr key={b.id} className="border-b border-slate-100">
                  <td className="py-2 pr-4">{DAYS[b.day_of_week]}</td>
                  <td className="py-2 pr-4">{b.start_time}</td>
                  <td className="py-2 pr-4">{b.end_time}</td>
                  <td className="py-2 pr-4 text-xs text-slate-500">{b.reason ?? "—"}</td>
                  {canManage ? (
                    <td className="py-2 pr-4">
                      <DeleteButton action={deleteRecurringBlockAction.bind(null, b.id)} />
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Availability exceptions */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Date exceptions</h2>
          {canManage ? <AddExceptionDialog /> : null}
        </div>
        <p className="text-sm text-slate-500">
          One-off overrides for specific dates: full closure or special hours.
        </p>
        {exceptions.length === 0 ? (
          <p className="text-sm text-slate-500">No exceptions configured.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs uppercase text-slate-500">
                <th scope="col" className="py-2 pr-4">Date</th>
                <th scope="col" className="py-2 pr-4">Type</th>
                <th scope="col" className="py-2 pr-4">Hours</th>
                <th scope="col" className="py-2 pr-4">Reason</th>
                {canManage ? <th scope="col" className="py-2 pr-4">Actions</th> : null}
              </tr>
            </thead>
            <tbody>
              {exceptions.map((exc) => (
                <tr key={exc.id} className="border-b border-slate-100">
                  <td className="py-2 pr-4">{exc.date}</td>
                  <td className="py-2 pr-4">
                    {exc.is_closed ? (
                      <span className="rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                        Closed
                      </span>
                    ) : (
                      <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                        Special hours
                      </span>
                    )}
                  </td>
                  <td className="py-2 pr-4 text-xs text-slate-500">
                    {exc.is_closed ? "—" : `${exc.start_time} – ${exc.end_time}`}
                  </td>
                  <td className="py-2 pr-4 text-xs text-slate-500">{exc.reason ?? "—"}</td>
                  {canManage ? (
                    <td className="py-2 pr-4">
                      <DeleteButton action={deleteExceptionAction.bind(null, exc.id)} />
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
