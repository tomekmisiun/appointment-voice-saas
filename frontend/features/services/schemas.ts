import { z } from "zod";

export const serviceFormSchema = z.object({
  name: z.string().trim().min(1, "Name is required").max(255, "Name must be 255 characters or fewer"),
  duration_minutes: z.coerce
    .number()
    .int("Duration must be a whole number")
    .min(1, "Duration must be at least 1 minute")
    .max(480, "Duration must be 480 minutes or fewer"),
  price_minor_units: z.coerce
    .number()
    .int("Price must be a whole number (minor units)")
    .min(0, "Price cannot be negative")
    .optional()
    .or(z.literal("")),
  currency: z
    .string()
    .trim()
    .length(3, "Currency must be a 3-letter code (e.g. PLN)")
    .optional()
    .or(z.literal("")),
});

export type ServiceFormValues = z.infer<typeof serviceFormSchema>;
