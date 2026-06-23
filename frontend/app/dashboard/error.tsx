"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { StateMessage } from "@/components/ui/StateMessage";

export default function DashboardError({ error, reset }: { error: Error; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <StateMessage
      tone="error"
      title="Something went wrong loading the dashboard"
      description="This was logged. You can try again, or log out and back in if the problem continues."
      action={<Button onClick={reset}>Try again</Button>}
    />
  );
}
