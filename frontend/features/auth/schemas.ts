import { z } from "zod";
import { emailSchema, passwordSchema } from "@/lib/validation/common";

// Shared by the client-side login form (React Hook Form resolver) and the
// /api/auth/login Route Handler's own input validation — one definition,
// so the two can never silently drift apart.
export const loginRequestSchema = z.object({
  email: emailSchema,
  password: passwordSchema,
});

export type LoginRequest = z.infer<typeof loginRequestSchema>;
