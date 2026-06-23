/** Formats an ISO datetime in the business's own timezone — never the browser's. */
export function formatInBusinessTimezone(isoDateTime: string, timeZone: string): string {
  return new Intl.DateTimeFormat(undefined, {
    timeZone,
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(isoDateTime));
}

// BookingRead.status is generated as a plain `string`, not the
// BookingStatus enum (see BookingStatusBadge for why) — accept string here
// too rather than a type that doesn't match what callers actually have.
export function bookingStatusLabel(status: string): string {
  switch (status) {
    case "confirmed":
      return "Confirmed";
    case "cancelled":
      return "Cancelled";
    default:
      return status;
  }
}

/** Builds a small id->name lookup from a bounded list (staff, services) — never an N+1 fetch per row. */
export function buildIdNameMap(items: { id: number; name: string }[]): Map<number, string> {
  return new Map(items.map((item) => [item.id, item.name]));
}
