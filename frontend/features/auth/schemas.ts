import { z } from "zod";
import { emailSchema, passwordSchema } from "@/lib/validation/common";

// Shared by the client-side login form (React Hook Form resolver) and the
// /api/auth/login Route Handler's own input validation — one definition,
// so the two can never silently drift apart.
export const loginRequestSchema = z.object({
  workspace: z
    .union([
      z.literal(""),
      z.string().trim().min(2, "Enter a valid workspace").max(63).regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "Use lowercase letters, numbers and hyphens"),
    ])
    .optional(),
  email: emailSchema,
  password: passwordSchema,
});

export type LoginRequest = z.infer<typeof loginRequestSchema>;

export const registerRequestSchema = z.object({
  salon_name: z.string().trim().min(1, "Business name is required").max(255),
  admin_email: emailSchema,
  admin_password: z.string().min(8, "Password must be at least 8 characters"),
});

export type RegisterRequest = z.infer<typeof registerRequestSchema>;
