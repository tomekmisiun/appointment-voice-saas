import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { BusinessRead } from "@/lib/api/types";
import { TelephonyStatusCard } from "./TelephonyStatusCard";

function business(overrides: Partial<BusinessRead> = {}): BusinessRead {
  return {
    id: 1,
    tenant_id: 1,
    name: "Glamour Studio Demo",
    timezone: "Europe/Warsaw",
    language: "en",
    phone: "+18174057514",
    owner_notification_phone: "+48505460409",
    transfer_phone_number: "+48505460409",
    is_active: true,
    transfer_enabled: true,
    transfer_destination_policy: "business_phone",
    booking_mode: "internal_booking",
    external_booking_url: null,
    external_booking_label: null,
    external_booking_provider: null,
    subscription_plan: "full_booking",
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

describe("TelephonyStatusCard", () => {
  beforeEach(() => {
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  it("renders the configured demo Voice number and copies the E.164 value", async () => {
    render(<TelephonyStatusCard business={business()} isDemo />);

    expect(screen.getByText("+1 (817) 405-7514")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.queryByText("+1 (000) 000-0000")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Copy phone number" }));

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("+18174057514");
    await waitFor(() => expect(screen.getByText("Copied!")).toBeInTheDocument());
  });

  it("does not show Active when the Voice number is missing", () => {
    render(<TelephonyStatusCard business={business({ phone: null })} />);

    expect(screen.getByText("Not configured")).toBeInTheDocument();
    expect(screen.queryByText("Active")).not.toBeInTheDocument();
    expect(screen.getByText(/No voice number configured/)).toBeInTheDocument();
  });

  it("masks the demo owner notification number instead of exposing the full value", () => {
    render(<TelephonyStatusCard business={business()} isDemo />);

    expect(screen.getByText("+48 *** *** 409")).toBeInTheDocument();
    expect(screen.queryByText("+48505460409")).not.toBeInTheDocument();
    expect(screen.queryByText(/No notification number configured/)).not.toBeInTheDocument();
  });
});
