import { redirect } from "next/navigation";
import { SetupStatusCard } from "@/features/dashboard/components/SetupStatusCard";
import { TelephonyStatusCard } from "@/features/dashboard/components/TelephonyStatusCard";
import { getCurrentBusinessContextOrRefresh } from "@/features/dashboard/current-business";
import { getSetupStatus } from "@/features/dashboard/setup-status";
import { getSession } from "@/lib/auth/server";

export default async function DashboardOverviewPage() {
  const session = await getSession();
  if (!session) {
    redirect("/login");
  }

  // The layout above already resolved (and would have redirected on) the
  // 0/multiple-business states — this call is memoized via React's
  // cache() for the same accessToken, so it's not a second network call.
  const context = await getCurrentBusinessContextOrRefresh(session.accessToken, "/dashboard");
  if (context.kind !== "single") {
    return null;
  }

  const setupStatus = await getSetupStatus(session.accessToken, context.business.id);
  const isDemo = context.user.is_demo_user;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">{context.business.name}</h1>
        <p className="text-sm text-slate-500">{context.business.timezone}</p>
      </div>
      <SetupStatusCard status={setupStatus} />
      <TelephonyStatusCard business={context.business} isDemo={isDemo} />
      <p className="text-xs text-slate-400">
        Booking counts and other metrics aren&apos;t shown here yet — the backend owner-metrics
        endpoint doesn&apos;t exist yet (see docs/frontend/frontend-roadmap.md, task 13).
      </p>
    </div>
  );
}
