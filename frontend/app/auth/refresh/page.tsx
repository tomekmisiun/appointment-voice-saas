import { RefreshAndRedirect } from "@/features/auth/components/RefreshAndRedirect";
import { DEFAULT_REFRESH_REDIRECT_TARGET, isSafeInternalPath } from "@/lib/auth/constants";

/**
 * Navigable entry point for the refresh flow. Deliberately does no
 * mutation itself (no cookie read/write, no backend call) — it only
 * validates `next` and renders the Client Component that triggers the
 * actual refresh via a Server Action. See lib/auth/actions.ts for why a
 * Server Action is used here instead of a GET handler that mutates.
 */
export default async function RefreshPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const params = await searchParams;
  const requestedNext = params.next ?? DEFAULT_REFRESH_REDIRECT_TARGET;
  const next = isSafeInternalPath(requestedNext) ? requestedNext : DEFAULT_REFRESH_REDIRECT_TARGET;

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <p className="text-sm text-slate-600" role="status">
        Signing you back in…
      </p>
      <RefreshAndRedirect next={next} />
    </main>
  );
}
