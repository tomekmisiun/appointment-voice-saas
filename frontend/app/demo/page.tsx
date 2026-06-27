"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

/**
 * Public demo entry point. On mount, calls the BFF /api/auth/demo endpoint
 * to start a read-only demo session, then hard-navigates to /dashboard.
 * Hard navigation (window.location) is required so the Server Component
 * rendered inside /dashboard sees the freshly-set session cookie.
 */
export default function DemoPage() {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function startDemo() {
      try {
        const resp = await fetch("/api/auth/demo", { method: "POST" });

        if (resp.ok) {
          window.location.assign("/dashboard");
          return;
        }

        const json = await resp.json().catch(() => null);
        setError(
          json?.error?.message ??
            "The demo is temporarily unavailable. Please try again later.",
        );
      } catch {
        setError("Could not connect to the server. Please try again.");
      } finally {
        setLoading(false);
      }
    }

    startDemo();
  }, []);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50">
        <p className="text-sm text-slate-500">Starting demo…</p>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm text-center">
        <p role="alert" className="mb-4 text-sm text-red-600">
          {error}
        </p>
        <Link
          href="/login"
          className="text-sm text-slate-600 underline hover:text-slate-900"
        >
          Back to sign in
        </Link>
      </div>
    </main>
  );
}
