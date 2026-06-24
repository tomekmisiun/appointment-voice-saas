import { z } from "zod";

// Normalizes to a trimmed string, always "" for blank rather than
// undefined/null: the backend's PATCH (update_staff) only assigns `phone`
// when the value is not None, so sending null/omitting it is silently
// ignored and can never clear an existing phone number. An empty string
// is the only value the existing contract actually lets us use to clear
// it — both create and update send this same normalized value.
const optionalPhone = z
  .string()
  .trim()
  .max(32, "Phone must be 32 characters or fewer")
  .optional()
  .or(z.literal(""))
  .transform((value) => value ?? "");

export const staffFormSchema = z.object({
  name: z.string().trim().min(1, "Name is required").max(255, "Name must be 255 characters or fewer"),
  phone: optionalPhone,
});

export type StaffFormValues = z.infer<typeof staffFormSchema>;
