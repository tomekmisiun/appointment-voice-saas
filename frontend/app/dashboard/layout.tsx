import { redirect } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { getCurrentBusinessContextOrRefresh } from "@/features/dashboard/current-business";
import { MultipleBusinessesState } from "@/features/dashboard/components/MultipleBusinessesState";
import { NoBusinessState } from "@/features/dashboard/components/NoBusinessState";
import { getSession, isAccessTokenExpired } from "@/lib/auth/server";

/**
 * The actual auth enforcement boundary for every /dashboard/* route — not
 * middleware (see lib/auth/actions.ts for why). Reads the session cookie
 * directly and fetches FastAPI while the token looks valid; never
 * refreshes here (Server Components must not — see the refresh flow).
 */
export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession();

  if (!session) {
    redirect("/login");
  }

  if (isAccessTokenExpired(session)) {
    redirect("/auth/refresh?next=/dashboard");
  }

  const context = await getCurrentBusinessContextOrRefresh(session.accessToken, "/dashboard");

  if (context.kind === "none") {
    return <NoBusinessState />;
  }

  if (context.kind === "multiple") {
    return <MultipleBusinessesState businesses={context.businesses} />;
  }

  return (
    <AppShell business={context.business} user={context.user}>
      <QueryProvider>{children}</QueryProvider>
    </AppShell>
  );
}
