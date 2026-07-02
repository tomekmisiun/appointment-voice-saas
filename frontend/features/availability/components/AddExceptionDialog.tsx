"use client";

import { useActionState, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { createExceptionAction, type AvailabilityActionResult } from "../actions";

const initialState: AvailabilityActionResult = { ok: true };

function ExceptionForm({ onClose }: { onClose: () => void }) {
  const formRef = useRef<HTMLFormElement>(null);
  const [isClosed, setIsClosed] = useState(true);
  const [state, formAction, isPending] = useActionState(createExceptionAction, initialState);

  useEffect(() => {
    if (state !== initialState && state.ok) {
      onClose();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state]);

  return (
    <form ref={formRef} action={formAction} className="mt-4 space-y-3">
      <div>
        <label htmlFor="exc-date" className="block text-sm font-medium text-slate-700">
          Date
        </label>
        <input
          id="exc-date"
          name="date"
          type="date"
          required
          className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
        />
      </div>
      <div className="flex items-center gap-2">
        <input
          id="exc-closed"
          name="is_closed"
          type="checkbox"
          value="true"
          checked={isClosed}
          onChange={(e) => setIsClosed(e.target.checked)}
          className="rounded border-slate-300"
        />
        <label htmlFor="exc-closed" className="text-sm font-medium text-slate-700">
          Fully closed (no appointments)
        </label>
      </div>
      {!isClosed && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="exc-start" className="block text-sm font-medium text-slate-700">
              Start
            </label>
            <input
              id="exc-start"
              name="start_time"
              type="time"
              required
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
          </div>
          <div>
            <label htmlFor="exc-end" className="block text-sm font-medium text-slate-700">
              End
            </label>
            <input
              id="exc-end"
              name="end_time"
              type="time"
              required
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
          </div>
        </div>
      )}
      <div>
        <label htmlFor="exc-reason" className="block text-sm font-medium text-slate-700">
          Reason (optional)
        </label>
        <input
          id="exc-reason"
          name="reason"
          type="text"
          className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
          placeholder="e.g. Public holiday"
        />
      </div>

      {!state.ok && state.error ? (
        <p role="alert" className="text-sm text-red-600">
          {state.error}
        </p>
      ) : null}

      <div className="flex justify-end gap-3 pt-2">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" disabled={isPending}>
          {isPending ? "Adding…" : "Save"}
        </Button>
      </div>
    </form>
  );
}

export function AddExceptionDialog() {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [formKey, setFormKey] = useState(0);

  function openDialog() {
    setFormKey((k) => k + 1);
    dialogRef.current?.showModal();
  }

  function closeDialog() {
    dialogRef.current?.close();
  }

  return (
    <>
      <Button type="button" onClick={openDialog}>
        Add exception
      </Button>
      <dialog
        ref={dialogRef}
        aria-labelledby="add-exc-title"
        className="w-full max-w-sm rounded-lg border border-slate-200 p-6 shadow-lg backdrop:bg-slate-900/40"
      >
        <h2 id="add-exc-title" className="text-lg font-semibold text-slate-900">
          Add availability exception
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Override availability for a specific date (e.g. holiday or special hours).
        </p>
        <ExceptionForm key={formKey} onClose={closeDialog} />
      </dialog>
    </>
  );
}
