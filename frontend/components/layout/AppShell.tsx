"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogoutButton } from "@/features/auth/components/LogoutButton";
import { NAV_ITEMS } from "./nav-items";
import type { BusinessRead, UserRead } from "@/lib/api/types";

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <nav aria-label="Dashboard sections" className="flex flex-col gap-1">
      {NAV_ITEMS.map((item) => {
        const isActive = pathname === item.href;

        if (item.status === "coming-soon") {
          return (
            <span
              key={item.href}
              className="flex items-center justify-between rounded-md px-3 py-2 text-sm text-slate-400"
              aria-disabled="true"
            >
              {item.label}
              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">Coming soon</span>
            </span>
          );
        }

        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={isActive ? "page" : undefined}
            className={`rounded-md px-3 py-2 text-sm font-medium ${
              isActive ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function AppShell({
  business,
  user,
  children,
}: {
  business: BusinessRead;
  user: UserRead;
  children: React.ReactNode;
}) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2 focus:shadow"
      >
        Skip to content
      </a>

      {user.is_demo_user ? (
        <div
          role="banner"
          aria-label="Demo mode"
          className="sticky top-0 z-40 flex items-center justify-center gap-2 bg-amber-50 border-b border-amber-200 px-4 py-2 text-sm font-medium text-amber-800"
        >
          <span>Public demo — browse the platform and test the phone number. Data changes are disabled.</span>
        </div>
      ) : null}

      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 md:px-6">
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="rounded-md p-2 text-slate-600 hover:bg-slate-100 md:hidden"
            aria-expanded={mobileNavOpen}
            aria-controls="mobile-nav"
            aria-label="Toggle navigation menu"
            onClick={() => setMobileNavOpen((open) => !open)}
          >
            <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.75 6.75h16.5M3.75 12h16.5M3.75 17.25h16.5" />
            </svg>
          </button>
          <div>
            <p className="text-sm font-semibold text-slate-900">{business.name}</p>
            <p className="text-xs text-slate-500">
              {business.booking_mode === "external_booking_link" ? "External booking link" : "Internal booking"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden text-sm text-slate-600 sm:inline">{user.email}</span>
          <LogoutButton />
        </div>
      </header>

      <div className="flex">
        <aside className="hidden w-56 shrink-0 border-r border-slate-200 bg-white px-3 py-4 md:block">
          <NavList />
        </aside>

        {mobileNavOpen ? (
          <div className="fixed inset-0 z-40 md:hidden">
            <button
              type="button"
              aria-label="Close navigation menu"
              className="absolute inset-0 bg-slate-900/40"
              onClick={() => setMobileNavOpen(false)}
            />
            <div id="mobile-nav" className="absolute left-0 top-0 h-full w-64 bg-white px-3 py-4 shadow-lg">
              <NavList onNavigate={() => setMobileNavOpen(false)} />
            </div>
          </div>
        ) : null}

        <main id="main-content" className="flex-1 px-4 py-6 md:px-6">
          {children}
        </main>
      </div>
    </div>
  );
}
