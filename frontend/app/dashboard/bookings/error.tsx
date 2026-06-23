"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { StateMessage } from "@/components/ui/StateMessage";

export default function BookingsError({ error, reset }: { error: Error; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <StateMessage
      tone="error"
      title="Something went wrong loading bookings"
      description="This was logged. You can try again, or go back to the dashboard."
      action={<Button onClick={reset}>Try again</Button>}
    />
  );
}
