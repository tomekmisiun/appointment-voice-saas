import { NextResponse } from "next/server";
import { postToBackendUnauthenticated } from "@/lib/api/server";
import { withCsrfProtection } from "@/lib/auth/csrf";
import { clearSession, getSession } from "@/lib/auth/server";

export const POST = withCsrfProtection(async () => {
  const session = await getSession();

  if (session) {
    try {
      await postToBackendUnauthenticated("/api/v1/auth/logout", {
        refresh_token: session.refreshToken,
      });
    } catch {
      // Best-effort: clearing the local cookie below is what actually ends
      // the session from this app's point of view. If the backend call
      // fails (token already expired/revoked, transient network issue),
      // the user must still be able to log out rather than get stuck.
    }
  }

  await clearSession();
  return NextResponse.json({ ok: true });
});
