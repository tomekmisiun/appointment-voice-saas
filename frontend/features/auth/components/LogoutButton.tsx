"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";

export function LogoutButton() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLogout() {
    if (pending) return;
    setPending(true);
    setError(null);

    try {
      const response = await fetch("/api/auth/logout", { method: "POST" });
      if (!response.ok) {
        throw new Error("logout_failed");
      }
      // Hard navigation, not router.push: guarantees no stale
      // client-side cache of authenticated data survives the logout.
      window.location.assign("/");
    } catch {
      setError("Could not log out. Please try again.");
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <Button variant="secondary" type="button" onClick={handleLogout} disabled={pending}>
        {pending ? "Signing out…" : "Log out"}
      </Button>
      {error ? (
        <p role="alert" className="max-w-48 text-right text-xs text-red-600">
          {error}
        </p>
      ) : null}
    </div>
  );
}
