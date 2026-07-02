"use client";

import { useActionState } from "react";
import { Button } from "@/components/ui/Button";
import { setServiceActiveAction, type ServiceActionResult } from "../actions";

const initialState: ServiceActionResult = { ok: true };

export function ToggleServiceActiveButton({
  serviceId,
  isActive,
}: {
  serviceId: number;
  isActive: boolean;
}) {
  const [state, dispatch, isPending] = useActionState<ServiceActionResult, FormData>(
    () => setServiceActiveAction(serviceId, !isActive),
    initialState,
  );

  return (
    <form action={dispatch}>
      <Button type="submit" variant="secondary" disabled={isPending}>
        {isPending ? "Updating…" : isActive ? "Deactivate" : "Reactivate"}
      </Button>
      {!state.ok && state.error ? (
        <p role="alert" className="mt-1 text-xs text-red-600">
          {state.error}
        </p>
      ) : null}
    </form>
  );
}
