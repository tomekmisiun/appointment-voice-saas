"use client";

import { useEffect } from "react";
import { refreshSessionAction } from "@/lib/auth/actions";

/**
 * Fires the refresh Server Action on mount. Under React Strict Mode this
 * effect runs twice in development by design — refreshSessionAction's
 * single-flight de-dup exists specifically so that double-invocation (or
 * two tabs hitting the same server process) share one backend call instead
 * of racing the backend's single-use refresh token. See lib/auth/actions.ts.
 */
export function RefreshAndRedirect({ next }: { next: string }) {
  useEffect(() => {
    void refreshSessionAction(next);
  }, [next]);

  return null;
}
