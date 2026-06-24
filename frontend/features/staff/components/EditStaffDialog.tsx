"use client";

import { useActionState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/Button";
import type { StaffRead } from "@/lib/api/types";
import { updateStaffAction, type StaffActionResult } from "../actions";

const initialState: StaffActionResult = { ok: true };

export function EditStaffDialog({ staff }: { staff: StaffRead }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [state, formAction, isPending] = useActionState(
    updateStaffAction.bind(null, staff.id),
    initialState,
  );

  useEffect(() => {
    if (state !== initialState && state.ok) {
      dialogRef.current?.close();
    }
  }, [state]);

  return (
    <>
      <Button type="button" variant="secondary" onClick={() => dialogRef.current?.showModal()}>
        Edit
      </Button>
      <dialog
        ref={dialogRef}
        aria-labelledby={`edit-staff-title-${staff.id}`}
        className="w-full max-w-sm rounded-lg border border-slate-200 p-6 shadow-lg backdrop:bg-slate-900/40"
      >
        <h2 id={`edit-staff-title-${staff.id}`} className="text-lg font-semibold text-slate-900">
          Edit {staff.name}
        </h2>
        <form action={formAction} className="mt-4 space-y-3">
          <div>
            <label htmlFor={`edit-staff-name-${staff.id}`} className="block text-sm font-medium text-slate-700">
              Name
            </label>
            <input
              id={`edit-staff-name-${staff.id}`}
              name="name"
              type="text"
              required
              defaultValue={staff.name}
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
          </div>
          <div>
            <label htmlFor={`edit-staff-phone-${staff.id}`} className="block text-sm font-medium text-slate-700">
              Phone (optional)
            </label>
            <input
              id={`edit-staff-phone-${staff.id}`}
              name="phone"
              type="text"
              defaultValue={staff.phone ?? ""}
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
              {isPending ? "Saving…" : "Save changes"}
            </Button>
          </div>
        </form>
      </dialog>
    </>
  );
}
