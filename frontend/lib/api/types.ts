// Re-exports of generated backend response types (see schema.gen.ts, produced
// by `pnpm api:generate` from the live FastAPI OpenAPI schema). Importing
// these instead of hand-writing matching interfaces is what keeps the
// frontend's types checked against the real backend contract — see
// `pnpm api:check` for drift detection.
import type { components } from "./schema.gen";

export type Token = components["schemas"]["Token"];
export type UserRead = components["schemas"]["UserRead"];
export type BusinessRead = components["schemas"]["BusinessRead"];
export type StaffRead = components["schemas"]["StaffRead"];
export type ServiceRead = components["schemas"]["ServiceRead"];
export type WorkingHoursRead = components["schemas"]["WorkingHoursRead"];
