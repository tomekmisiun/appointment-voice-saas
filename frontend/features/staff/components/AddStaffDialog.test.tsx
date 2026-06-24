import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AddStaffDialog } from "./AddStaffDialog";

vi.mock("../actions", () => ({
  createStaffAction: vi.fn(),
}));

import { createStaffAction } from "../actions";

describe("AddStaffDialog", () => {
  it("opens the dialog and submits the form to createStaffAction", async () => {
    vi.mocked(createStaffAction).mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    render(<AddStaffDialog />);

    await user.click(screen.getByRole("button", { name: "Add staff" }));
    expect(screen.getByRole("heading", { name: "Add staff" })).toBeVisible();

    await user.type(screen.getByLabelText(/name/i), "Alice");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(createStaffAction).toHaveBeenCalled());
  });

  it("shows the server-returned error inline", async () => {
    vi.mocked(createStaffAction).mockResolvedValue({ ok: false, error: "Name already in use" });
    const user = userEvent.setup();
    render(<AddStaffDialog />);

    await user.click(screen.getByRole("button", { name: "Add staff" }));
    await user.type(screen.getByLabelText(/name/i), "Alice");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Name already in use");
  });
});
