"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import type { AvailabilitySlot } from "@/lib/api/types";
import { useAvailabilityQuery, useRescheduleBookingMutation } from "../api";
import { formatTimeInBusinessTimezone, todayInTimezone } from "../utils";

/**
 * Native <dialog>, same pattern as CancelBookingDialog. Slot picker is
 * scoped to the booking's own service/staff (the backend's reschedule
 * keeps both fixed — see app/api/bookings/[bookingId]/reschedule/route.ts)
 * and one date at a time (the availability endpoint takes a single date,
 * not a range).
 *
 * Rescheduling creates a *new* booking (the old one is cancelled
 * underneath) — on success this navigates to the new booking's URL via
 * router.push, not router.refresh(), since the current URL's id is no
 * longer the live one.
 */
export function RescheduleBookingDialog({
  bookingId,
  serviceId,
  staffId,
  timezone,
}: {
  bookingId: number;
  serviceId: number;
  staffId: number | null;
  timezone: string;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [date, setDate] = useState(() => todayInTimezone(timezone));
  const [selectedSlot, setSelectedSlot] = useState<AvailabilitySlot | null>(null);
  const [reason, setReason] = useState("");
  const router = useRouter();
  const mutation = useRescheduleBookingMutation(bookingId);
  // Gated on isOpen: must not fetch (or show stale data) before the admin
  // has actually opened the dialog — see useAvailabilityQuery's doc
  // comment and the cross-provider review finding that flagged this.
  const availability = useAvailabilityQuery({ serviceId, staffId, date }, isOpen);

  function openDialog() {
    mutation.reset();
    setSelectedSlot(null);
    setReason("");
    setIsOpen(true);
    dialogRef.current?.showModal();
  }

  function closeDialog() {
    dialogRef.current?.close();
  }

  // Native close (Escape key) bypasses closeDialog()'s click handler —
  // this <dialog> "close" event is the one place that's always called
  // regardless of how it closed, so it's the reliable spot to sync isOpen.
  function handleDialogClose() {
    setIsOpen(false);
  }

  function handleDateChange(value: string) {
    setDate(value);
    setSelectedSlot(null);
  }

  async function handleConfirm() {
    if (!selectedSlot) {
      return;
    }
    try {
      const newBooking = await mutation.mutateAsync({
        newStartsAt: selectedSlot.starts_at,
        reason: reason.trim() || undefined,
      });
      closeDialog();
      router.push(`/dashboard/bookings/${newBooking.id}`);
    } catch {
      // Surfaced below via mutation.isError; nothing further to do here.
    }
  }

  return (
    <>
      <Button type="button" variant="secondary" onClick={openDialog}>
        Reschedule
      </Button>
      <dialog
        ref={dialogRef}
        onClose={handleDialogClose}
        aria-labelledby="reschedule-booking-title"
        className="w-full max-w-md rounded-lg border border-slate-200 p-6 shadow-lg backdrop:bg-slate-900/40"
      >
        <h2 id="reschedule-booking-title" className="text-lg font-semibold text-slate-900">
          Reschedule this booking
        </h2>

        <label htmlFor="reschedule-date" className="mt-4 block text-sm font-medium text-slate-700">
          New date
        </label>
        <input
          id="reschedule-date"
          type="date"
          value={date}
          min={todayInTimezone(timezone)}
          onChange={(event) => handleDateChange(event.target.value)}
          className="mt-1 rounded-md border border-slate-300 px-2 py-1 text-sm"
        />

        <fieldset className="mt-4">
          <legend className="text-sm font-medium text-slate-700">Available times</legend>
          <div className="mt-2" role="radiogroup" aria-label="Available times">
            {availability.isPending || availability.isFetching ? (
              // isPending covers "no data at all yet" (including while the
              // dialog is closed and the query is disabled). isFetching
              // additionally covers every background refetch (reopening
              // the dialog with staleTime: 0, or changing the date) —
              // previously cached slots from a prior fetch must never
              // stay clickable while a fresh one is in flight, or an admin
              // could pick a slot that's already gone stale.
              <p role="status" className="text-sm text-slate-500">
                Loading available times…
              </p>
            ) : availability.isError ? (
              <p role="alert" className="text-sm text-red-600">
                Couldn&apos;t load availability for this date.
              </p>
            ) : availability.data.length === 0 ? (
              <p className="text-sm text-slate-500">No available times on this date.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {availability.data.map((slot) => {
                  const isSelected = selectedSlot?.starts_at === slot.starts_at;
                  return (
                    <button
                      key={slot.starts_at}
                      type="button"
                      role="radio"
                      aria-checked={isSelected}
                      onClick={() => setSelectedSlot(slot)}
                      className={`rounded-md border px-3 py-1 text-sm ${
                        isSelected
                          ? "border-slate-900 bg-slate-900 text-white"
                          : "border-slate-300 text-slate-700 hover:bg-slate-50"
                      }`}
                    >
                      {formatTimeInBusinessTimezone(slot.starts_at, timezone)}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </fieldset>

        <label htmlFor="reschedule-reason" className="mt-4 block text-sm font-medium text-slate-700">
          Reason (optional)
        </label>
        <textarea
          id="reschedule-reason"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          maxLength={255}
          rows={2}
          className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
        />

        {mutation.isError ? (
          <p role="alert" className="mt-2 text-sm text-red-600">
            {mutation.error instanceof Error ? mutation.error.message : "Couldn't reschedule this booking."}
          </p>
        ) : null}

        <div className="mt-4 flex justify-end gap-3">
          <Button type="button" variant="secondary" onClick={closeDialog} disabled={mutation.isPending}>
            Close
          </Button>
          <Button
            type="button"
            onClick={handleConfirm}
            disabled={!selectedSlot || mutation.isPending}
          >
            {mutation.isPending ? "Rescheduling…" : "Confirm new time"}
          </Button>
        </div>
      </dialog>
    </>
  );
}
