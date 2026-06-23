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

/** Time-only, in the business's own timezone — for a same-day slot picker list. */
export function formatTimeInBusinessTimezone(isoDateTime: string, timeZone: string): string {
  return new Intl.DateTimeFormat(undefined, { timeZone, timeStyle: "short" }).format(
    new Date(isoDateTime),
  );
}

/**
 * "Today" as YYYY-MM-DD in the given timezone — not the browser's. The
 * en-CA locale formats dates as YYYY-MM-DD, which doubles as a reliable
 * way to extract that shape from Intl without manual string-splitting.
 */
export function todayInTimezone(timeZone: string): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone }).format(new Date());
}
