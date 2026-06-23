"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { useCancelBookingMutation } from "../api";

/**
 * Native <dialog> for the one destructive action in this branch — no
 * headless dialog library needed for a single confirm step. Only ever
 * rendered by the detail page when the signed-in user is an admin and the
 * booking is still confirmed (see app/dashboard/bookings/[bookingId]/page.tsx);
 * the backend's own require_role("admin") and the proxy route's own role
 * check are the real authorization boundary, not this component's
 * presence or absence.
 */
export function CancelBookingDialog({ bookingId }: { bookingId: number }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [reason, setReason] = useState("");
  const router = useRouter();
  const mutation = useCancelBookingMutation(bookingId);

  function openDialog() {
    mutation.reset();
    setReason("");
    dialogRef.current?.showModal();
  }

  function closeDialog() {
    dialogRef.current?.close();
  }

  async function handleConfirm() {
    try {
      await mutation.mutateAsync(reason.trim() || undefined);
      closeDialog();
      // The detail page is a Server Component — refresh it to show the
      // now-cancelled status instead of duplicating booking state here.
      router.refresh();
    } catch {
      // Surfaced below via mutation.isError; nothing further to do here.
    }
  }

  return (
    <>
      <Button type="button" variant="danger" onClick={openDialog}>
        Cancel booking
      </Button>
      <dialog
        ref={dialogRef}
        aria-labelledby="cancel-booking-title"
        className="rounded-lg border border-slate-200 p-6 shadow-lg backdrop:bg-slate-900/40"
      >
        <h2 id="cancel-booking-title" className="text-lg font-semibold text-slate-900">
          Cancel this booking?
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          This can&apos;t be undone from here. The slot will be freed.
        </p>

        <label htmlFor="cancel-reason" className="mt-4 block text-sm font-medium text-slate-700">
          Reason (optional)
        </label>
        <textarea
          id="cancel-reason"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          maxLength={255}
          rows={3}
          className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
        />

        {mutation.isError ? (
          <p role="alert" className="mt-2 text-sm text-red-600">
            {mutation.error instanceof Error ? mutation.error.message : "Couldn't cancel this booking."}
          </p>
        ) : null}

        <div className="mt-4 flex justify-end gap-3">
          <Button type="button" variant="secondary" onClick={closeDialog} disabled={mutation.isPending}>
            Keep booking
          </Button>
          <Button type="button" variant="danger" onClick={handleConfirm} disabled={mutation.isPending}>
            {mutation.isPending ? "Cancelling…" : "Yes, cancel booking"}
          </Button>
        </div>
      </dialog>
    </>
  );
}
