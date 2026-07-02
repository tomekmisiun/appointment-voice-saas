"use client";

import { useActionState } from "react";
import { Button } from "@/components/ui/Button";
import type { AvailabilityActionResult } from "../actions";

const initialState: AvailabilityActionResult = { ok: true };

export function DeleteButton({
  action,
  label = "Delete",
}: {
  action: () => Promise<AvailabilityActionResult>;
  label?: string;
}) {
  const [state, dispatch, isPending] = useActionState<AvailabilityActionResult, FormData>(
    () => action(),
    initialState,
  );

  return (
    <form action={dispatch}>
      <Button type="submit" variant="secondary" disabled={isPending}>
        {isPending ? "Deleting…" : label}
      </Button>
      {!state.ok && state.error ? (
        <p role="alert" className="mt-1 text-xs text-red-600">
          {state.error}
        </p>
      ) : null}
    </form>
  );
}
