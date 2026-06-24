import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { StaffRead } from "@/lib/api/types";
import { EditStaffDialog } from "./EditStaffDialog";

vi.mock("../actions", () => ({
  updateStaffAction: vi.fn(),
}));

import { updateStaffAction } from "../actions";

const staff: StaffRead = {
  id: 7,
  tenant_id: 1,
  business_id: 42,
  name: "Alice",
  phone: "555-1234",
  is_active: true,
  created_at: new Date().toISOString(),
};

describe("EditStaffDialog", () => {
  it("pre-fills the form with the staff member's current data", async () => {
    const user = userEvent.setup();
    render(<EditStaffDialog staff={staff} />);

    await user.click(screen.getByRole("button", { name: "Edit" }));

    expect(screen.getByLabelText(/name/i)).toHaveValue("Alice");
    expect(screen.getByLabelText(/phone/i)).toHaveValue("555-1234");
  });

  it("submits to updateStaffAction bound to this staff member's id", async () => {
    vi.mocked(updateStaffAction).mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    render(<EditStaffDialog staff={staff} />);

    await user.click(screen.getByRole("button", { name: "Edit" }));
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() => expect(updateStaffAction).toHaveBeenCalled());
    expect(vi.mocked(updateStaffAction).mock.calls[0]?.[0]).toBe(7);
  });
});
