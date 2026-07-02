"use client";

import { useActionState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/Button";
import { createRecurringBlockAction, type AvailabilityActionResult } from "../actions";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const initialState: AvailabilityActionResult = { ok: true };

export function AddRecurringBlockDialog() {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const [state, formAction, isPending] = useActionState(createRecurringBlockAction, initialState);

  useEffect(() => {
    if (state !== initialState && state.ok) {
      dialogRef.current?.close();
      formRef.current?.reset();
    }
  }, [state]);

  return (
    <>
      <Button type="button" onClick={() => dialogRef.current?.showModal()}>
        Add block
      </Button>
      <dialog
        ref={dialogRef}
        aria-labelledby="add-block-title"
        className="w-full max-w-sm rounded-lg border border-slate-200 p-6 shadow-lg backdrop:bg-slate-900/40"
      >
        <h2 id="add-block-title" className="text-lg font-semibold text-slate-900">
          Add recurring block
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          A recurring unavailable window, e.g. a weekly lunch break.
        </p>
        <form ref={formRef} action={formAction} className="mt-4 space-y-3">
          <div>
            <label htmlFor="block-day" className="block text-sm font-medium text-slate-700">
              Day
            </label>
            <select
              id="block-day"
              name="day_of_week"
              required
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
            >
              {DAYS.map((day, i) => (
                <option key={day} value={i}>
                  {day}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="block-start" className="block text-sm font-medium text-slate-700">
                Start
              </label>
              <input
                id="block-start"
                name="start_time"
                type="time"
                required
                className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
              />
            </div>
            <div>
              <label htmlFor="block-end" className="block text-sm font-medium text-slate-700">
                End
              </label>
              <input
                id="block-end"
                name="end_time"
                type="time"
                required
                className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
              />
            </div>
          </div>
          <div>
            <label htmlFor="block-reason" className="block text-sm font-medium text-slate-700">
              Reason (optional)
            </label>
            <input
              id="block-reason"
              name="reason"
              type="text"
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
              placeholder="e.g. Lunch break"
            />
          </div>

          {!state.ok && state.error ? (
            <p role="alert" className="text-sm text-red-600">
              {state.error}
            </p>
          ) : null}

          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="secondary" onClick={() => dialogRef.current?.close()}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? "Adding…" : "Save"}
            </Button>
          </div>
        </form>
      </dialog>
    </>
  );
}
