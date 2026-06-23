import { bookingStatusLabel } from "../utils";

// BookingRead.status is generated as a plain `string` (the backend schema
// declares `status: str`, not the BookingStatus enum) — so this takes a
// string and falls back gracefully instead of assuming only the two
// values we know about today.
const TONE_CLASSES: Record<string, string> = {
  confirmed: "bg-emerald-100 text-emerald-800",
  cancelled: "bg-slate-200 text-slate-600",
};

export function BookingStatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${
        TONE_CLASSES[status] ?? "bg-slate-100 text-slate-700"
      }`}
    >
      {bookingStatusLabel(status)}
    </span>
  );
}
