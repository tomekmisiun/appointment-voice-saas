"use client";

import { useActionState } from "react";
import { Button } from "@/components/ui/Button";
import { setStaffActiveAction, type StaffActionResult } from "../actions";

const initialState: StaffActionResult = { ok: true };

export function ToggleStaffActiveButton({ staffId, isActive }: { staffId: number; isActive: boolean }) {
  const [state, dispatch, isPending] = useActionState<StaffActionResult, FormData>(
    () => setStaffActiveAction(staffId, !isActive),
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
