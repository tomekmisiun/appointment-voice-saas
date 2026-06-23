import Link from "next/link";
import { StateMessage } from "@/components/ui/StateMessage";

export default function BookingNotFound() {
  return (
    <StateMessage
      title="Booking not found"
      description="This booking doesn't exist, or doesn't belong to this business."
      action={
        <Link href="/dashboard/bookings" className="text-sm text-blue-700 hover:underline">
          ← Back to bookings
        </Link>
      }
    />
  );
}
