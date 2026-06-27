"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const NAV_ITEMS = [
  { href: "/pricing", label: "Pricing" },
  { href: "/about", label: "About us" },
  { href: "/blog", label: "Blog" },
  { href: "/help", label: "Help centre" },
  { href: "/resources", label: "Resources" },
];

export function Brand() {
  return (
    <Link href="/" className="flex items-center gap-2.5 text-sm font-semibold text-white" aria-label="VoxSlot home">
      <span className="relative block h-7 w-7" aria-hidden="true">
        <span className="absolute left-0 top-2 h-3 w-3 rounded-sm bg-indigo-400" />
        <span className="absolute left-2 top-0 h-3 w-3 rounded-sm bg-violet-500" />
        <span className="absolute bottom-0 left-2 h-3 w-3 rounded-sm bg-blue-500" />
        <span className="absolute right-0 top-2 h-3 w-3 rounded-sm bg-indigo-300" />
      </span>
      <span>VoxSlot</span>
    </Link>
  );
}

export function PublicShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="marketing-surface min-h-screen bg-[#080d17] text-[#eef1f8]">
      <a href="#public-content" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-white focus:px-3 focus:py-2 focus:text-slate-950">
        Skip to content
      </a>
      <header className="relative z-40 mx-auto w-full max-w-6xl px-4 pt-4 sm:px-6">
        <div className="flex min-h-14 items-center justify-between rounded-lg border border-[#283246] bg-[#151c2a]/95 px-3 shadow-2xl shadow-black/20 backdrop-blur sm:px-4">
          <Brand />
          <nav aria-label="Public navigation" className="hidden items-center gap-7 lg:flex">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                aria-current={pathname === item.href ? "page" : undefined}
                className={`text-sm transition-colors ${pathname === item.href ? "text-white" : "text-[#b5bfd3] hover:text-white"}`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <div className="hidden items-center gap-2 sm:flex">
            <Link href="/login" className="rounded-md border border-[#2b364a] bg-[#202939] px-3 py-2 text-sm text-[#dbe1ec] transition-colors hover:bg-[#293449]">
              Sign in
            </Link>
            <Link href="/demo" className="rounded-md bg-indigo-500 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-400">
              Try demo
            </Link>
          </div>
          <button
            type="button"
            className="rounded-md border border-[#303a4d] px-3 py-2 text-sm text-white lg:hidden"
            aria-expanded={menuOpen}
            aria-controls="public-mobile-nav"
            onClick={() => setMenuOpen((open) => !open)}
          >
            Menu
          </button>
        </div>
        {menuOpen ? (
          <nav id="public-mobile-nav" aria-label="Mobile public navigation" className="mt-2 rounded-lg border border-[#283246] bg-[#151c2a] p-3 shadow-xl lg:hidden">
            {NAV_ITEMS.map((item) => (
              <Link key={item.href} href={item.href} onClick={() => setMenuOpen(false)} className="block rounded-md px-3 py-2.5 text-sm text-[#cbd3e2] hover:bg-[#202939] hover:text-white">
                {item.label}
              </Link>
            ))}
            <div className="mt-2 grid grid-cols-2 gap-2 border-t border-[#283246] pt-3">
              <Link href="/login" className="rounded-md border border-[#303a4d] px-3 py-2 text-center text-sm">Sign in</Link>
              <Link href="/demo" className="rounded-md bg-indigo-500 px-3 py-2 text-center text-sm font-medium">Try demo</Link>
            </div>
          </nav>
        ) : null}
      </header>

      <main id="public-content">{children}</main>

      <footer className="border-t border-[#1c2535] px-4 py-8 sm:px-6">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 text-sm text-[#7f8ba4] sm:flex-row sm:items-center sm:justify-between">
          <Brand />
          <p>Phone booking for appointment-led businesses.</p>
          <p>&copy; {new Date().getFullYear()} VoxSlot</p>
        </div>
      </footer>
    </div>
  );
}
