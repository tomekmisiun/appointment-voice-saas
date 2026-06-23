import { LogoutButton } from "@/features/auth/components/LogoutButton";
import { StateMessage } from "@/components/ui/StateMessage";

export function NoBusinessState() {
  return (
    <StateMessage
      title="No business is configured for this account"
      description="This account isn't set up to manage any active business yet. Contact an operator to finish onboarding before using the dashboard."
      action={<LogoutButton />}
    />
  );
}
