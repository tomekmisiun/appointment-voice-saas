"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { StateMessage } from "@/components/ui/StateMessage";

export default function BookingDetailError({ error, reset }: { error: Error; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <StateMessage
      tone="error"
      title="Something went wrong loading this booking"
      description="This was logged. You can try again, or go back to the bookings list."
      action={<Button onClick={reset}>Try again</Button>}
    />
  );
}
