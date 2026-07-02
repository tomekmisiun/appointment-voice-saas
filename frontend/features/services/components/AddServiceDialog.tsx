"use client";

import { useActionState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/Button";
import { createServiceAction, type ServiceActionResult } from "../actions";

const initialState: ServiceActionResult = { ok: true };

export function AddServiceDialog() {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const [state, formAction, isPending] = useActionState(createServiceAction, initialState);

  useEffect(() => {
    if (state !== initialState && state.ok) {
      dialogRef.current?.close();
      formRef.current?.reset();
    }
  }, [state]);

  return (
    <>
      <Button type="button" onClick={() => dialogRef.current?.showModal()}>
        Add service
      </Button>
      <dialog
        ref={dialogRef}
        aria-labelledby="add-service-title"
        className="w-full max-w-sm rounded-lg border border-slate-200 p-6 shadow-lg backdrop:bg-slate-900/40"
      >
        <h2 id="add-service-title" className="text-lg font-semibold text-slate-900">
          Add service
        </h2>
        <form ref={formRef} action={formAction} className="mt-4 space-y-3">
          <div>
            <label htmlFor="add-svc-name" className="block text-sm font-medium text-slate-700">
              Name
            </label>
            <input
              id="add-svc-name"
              name="name"
              type="text"
              required
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
          </div>
          <div>
            <label htmlFor="add-svc-duration" className="block text-sm font-medium text-slate-700">
              Duration (minutes)
            </label>
            <input
              id="add-svc-duration"
              name="duration_minutes"
              type="number"
              min={1}
              max={480}
              required
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
          </div>
          <div>
            <label htmlFor="add-svc-price" className="block text-sm font-medium text-slate-700">
              Price (minor units, optional)
            </label>
            <input
              id="add-svc-price"
              name="price_minor_units"
              type="number"
              min={0}
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
              placeholder="e.g. 5000 for 50.00"
            />
          </div>
          <div>
            <label htmlFor="add-svc-currency" className="block text-sm font-medium text-slate-700">
              Currency (optional)
            </label>
            <input
              id="add-svc-currency"
              name="currency"
              type="text"
              maxLength={3}
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
              placeholder="e.g. PLN"
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
