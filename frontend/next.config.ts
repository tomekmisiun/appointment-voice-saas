import type { NextConfig } from "next";

// No `experimental.serverActions.allowedOrigins` override: this app is
// served directly (no reverse proxy / different public origin), so
// Next.js's own default same-origin Server Action protection is sufficient.
// Route Handlers (login/logout) are protected separately via an explicit
// Origin/Referer check against APP_ORIGIN — see lib/auth/csrf.ts.
const nextConfig: NextConfig = {
  reactStrictMode: true,
};

export default nextConfig;
