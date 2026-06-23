import { z } from "zod";

// Shared primitives used by more than one feature's schema (currently just
// auth's login form + its Route Handler's own input validation — both need
// the same rules so client and server never disagree about what's valid).
export const emailSchema = z.string().trim().min(1, "Email is required").email("Enter a valid email address");
export const passwordSchema = z.string().min(1, "Password is required");
