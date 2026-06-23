"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";

export function LogoutButton() {
  const [pending, setPending] = useState(false);

  async function handleLogout() {
    setPending(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } finally {
      // Hard navigation, not router.push: guarantees no stale
      // client-side cache of authenticated data survives the logout.
      window.location.assign("/login");
    }
  }

  return (
    <Button variant="secondary" type="button" onClick={handleLogout} disabled={pending}>
      {pending ? "Signing out…" : "Log out"}
    </Button>
  );
}
