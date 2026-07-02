"use client";

import { useState, useTransition } from "react";
import { Button } from "@/components/ui/Button";
import type { BookingPublicRead } from "@/lib/api/types";
import {
  cancelPublicBookingAction,
  reschedulePublicBookingAction,
} from "@/features/booking-management/actions";

export function ManageBookingClient({
  token,
  booking,
}: {
  token: string;
  booking: BookingPublicRead;
}) {
  const [current, setCurrent] = useState(booking);
  const [view, setView] = useState<"idle" | "reschedule" | "rescheduled">("idle");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  if (current.status === "cancelled") {
    return (
      <p className="mt-6 rounded-md bg-slate-100 px-4 py-3 text-sm text-slate-600">
        This booking has been cancelled.
      </p>
    );
  }

  if (view === "rescheduled") {
    return (
      <p className="mt-6 rounded-md bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
        Your booking has been rescheduled. A new confirmation will be sent to you shortly.
      </p>
    );
  }

  function handleCancel() {
    setError(null);
    startTransition(async () => {
      const result = await cancelPublicBookingAction(token);
      if (result.ok && result.booking) {
        setCurrent(result.booking);
      } else {
        setError(result.error ?? "Something went wrong.");
      }
    });
  }

  function handleReschedule(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const raw = (form.elements.namedItem("new_starts_at") as HTMLInputElement).value;
    if (!raw) return;
    const newStartsAt = new Date(raw).toISOString();

    setError(null);
    startTransition(async () => {
      const result = await reschedulePublicBookingAction(token, newStartsAt);
      if (result.ok && result.booking) {
        setCurrent(result.booking);
        setView("rescheduled");
      } else {
        setError(result.error ?? "Something went wrong.");
      }
    });
  }

  return (
    <div className="mt-6 space-y-4">
      {error ? (
        <p role="alert" className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </p>
      ) : null}

      {view === "idle" ? (
        <div className="flex gap-3">
          <Button
            type="button"
            variant="secondary"
            onClick={() => setView("reschedule")}
            disabled={isPending}
          >
            Reschedule
          </Button>
          <Button
            type="button"
            onClick={handleCancel}
            disabled={isPending}
          >
            {isPending ? "Cancelling…" : "Cancel booking"}
          </Button>
        </div>
      ) : (
        <form onSubmit={handleReschedule} className="space-y-3">
          <div>
            <label
              htmlFor="new_starts_at"
              className="block text-sm font-medium text-slate-700"
            >
              New date & time
            </label>
            <input
              id="new_starts_at"
              name="new_starts_at"
              type="datetime-local"
              required
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
          </div>
          <div className="flex gap-3">
            <Button type="button" variant="secondary" onClick={() => setView("idle")} disabled={isPending}>
              Back
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? "Rescheduling…" : "Confirm reschedule"}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
