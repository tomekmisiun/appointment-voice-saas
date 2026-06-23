import type { HttpHandler } from "msw";

// Feature tests add their own handlers via `server.use(...)` per test;
// this default list intentionally stays empty so an unhandled request
// fails loudly (see tests/setup.ts `onUnhandledRequest: "error"`) instead
// of silently falling through to a generic mock.
export const handlers: HttpHandler[] = [];
