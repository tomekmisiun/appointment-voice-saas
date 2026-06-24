"use client";

import { useActionState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/Button";
import { createStaffAction, type StaffActionResult } from "../actions";

const initialState: StaffActionResult = { ok: true };

export function AddStaffDialog() {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const [state, formAction, isPending] = useActionState(createStaffAction, initialState);

  // useActionState re-renders with a new state object after the action
  // settles — `state !== initialState` is how we tell "a submission just
  // completed" apart from "never submitted yet" (both have ok: true).
  useEffect(() => {
    if (state !== initialState && state.ok) {
      dialogRef.current?.close();
      formRef.current?.reset();
    }
  }, [state]);

  return (
    <>
      <Button type="button" onClick={() => dialogRef.current?.showModal()}>
        Add staff
      </Button>
      <dialog
        ref={dialogRef}
        aria-labelledby="add-staff-title"
        className="w-full max-w-sm rounded-lg border border-slate-200 p-6 shadow-lg backdrop:bg-slate-900/40"
      >
        <h2 id="add-staff-title" className="text-lg font-semibold text-slate-900">
          Add staff
        </h2>
        <form ref={formRef} action={formAction} className="mt-4 space-y-3">
          <div>
            <label htmlFor="add-staff-name" className="block text-sm font-medium text-slate-700">
              Name
            </label>
            <input
              id="add-staff-name"
              name="name"
              type="text"
              required
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
          </div>
          <div>
            <label htmlFor="add-staff-phone" className="block text-sm font-medium text-slate-700">
              Phone (optional)
            </label>
            <input
              id="add-staff-phone"
              name="phone"
              type="text"
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
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
