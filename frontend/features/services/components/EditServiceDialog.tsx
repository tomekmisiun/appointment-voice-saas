"use client";

import { useActionState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/Button";
import type { ServiceRead } from "@/lib/api/types";
import { updateServiceAction, type ServiceActionResult } from "../actions";

const initialState: ServiceActionResult = { ok: true };

export function EditServiceDialog({ service }: { service: ServiceRead }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [state, formAction, isPending] = useActionState(
    updateServiceAction.bind(null, service.id),
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
        aria-labelledby={`edit-svc-title-${service.id}`}
        className="w-full max-w-sm rounded-lg border border-slate-200 p-6 shadow-lg backdrop:bg-slate-900/40"
      >
        <h2 id={`edit-svc-title-${service.id}`} className="text-lg font-semibold text-slate-900">
          Edit {service.name}
        </h2>
        <form action={formAction} className="mt-4 space-y-3">
          <div>
            <label htmlFor={`edit-svc-name-${service.id}`} className="block text-sm font-medium text-slate-700">
              Name
            </label>
            <input
              id={`edit-svc-name-${service.id}`}
              name="name"
              type="text"
              required
              defaultValue={service.name}
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
          </div>
          <div>
            <label htmlFor={`edit-svc-duration-${service.id}`} className="block text-sm font-medium text-slate-700">
              Duration (minutes)
            </label>
            <input
              id={`edit-svc-duration-${service.id}`}
              name="duration_minutes"
              type="number"
              min={1}
              max={480}
              required
              defaultValue={service.duration_minutes}
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
          </div>
          <div>
            <label htmlFor={`edit-svc-price-${service.id}`} className="block text-sm font-medium text-slate-700">
              Price (minor units, optional)
            </label>
            <input
              id={`edit-svc-price-${service.id}`}
              name="price_minor_units"
              type="number"
              min={0}
              defaultValue={service.price_minor_units ?? ""}
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
          </div>
          <div>
            <label htmlFor={`edit-svc-currency-${service.id}`} className="block text-sm font-medium text-slate-700">
              Currency (optional)
            </label>
            <input
              id={`edit-svc-currency-${service.id}`}
              name="currency"
              type="text"
              maxLength={3}
              defaultValue={service.currency ?? ""}
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
