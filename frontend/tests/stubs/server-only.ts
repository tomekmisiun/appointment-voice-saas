// Vitest stub for the `server-only` package. Next.js's own bundler
// substitutes this package with a no-op in Server Component contexts and
// makes it throw everywhere else (its actual job); Vitest doesn't have
// that bundler condition, so this alias (see vitest.config.ts) reproduces
// the same "no-op in server-side test code" behavior instead of failing
// every test that imports a server-only module.
export {};
