import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ToggleStaffActiveButton } from "./ToggleStaffActiveButton";

vi.mock("../actions", () => ({
  setStaffActiveAction: vi.fn(),
}));

import { setStaffActiveAction } from "../actions";

describe("ToggleStaffActiveButton", () => {
  it("shows 'Deactivate' for an active staff member and calls the action with the opposite value", async () => {
    vi.mocked(setStaffActiveAction).mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    render(<ToggleStaffActiveButton staffId={7} isActive />);

    const button = screen.getByRole("button", { name: "Deactivate" });
    await user.click(button);

    await waitFor(() => expect(setStaffActiveAction).toHaveBeenCalledWith(7, false));
  });

  it("shows 'Reactivate' for an inactive staff member and calls the action with the opposite value", async () => {
    vi.mocked(setStaffActiveAction).mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    render(<ToggleStaffActiveButton staffId={7} isActive={false} />);

    await user.click(screen.getByRole("button", { name: "Reactivate" }));

    await waitFor(() => expect(setStaffActiveAction).toHaveBeenCalledWith(7, true));
  });

  it("shows an inline error when the action fails", async () => {
    vi.mocked(setStaffActiveAction).mockResolvedValue({ ok: false, error: "Could not deactivate" });
    const user = userEvent.setup();
    render(<ToggleStaffActiveButton staffId={7} isActive />);

    await user.click(screen.getByRole("button", { name: "Deactivate" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Could not deactivate");
  });
});
