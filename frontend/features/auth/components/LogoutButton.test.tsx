import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LogoutButton } from "./LogoutButton";

describe("LogoutButton", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    vi.stubGlobal("location", { assign: vi.fn() });
  });

  it("posts to the logout BFF route, disables repeat clicks, and redirects to the landing page", async () => {
    const fetchMock = vi.mocked(fetch);
    let resolveLogout!: (response: Response) => void;
    fetchMock.mockReturnValue(
      new Promise<Response>((resolve) => {
        resolveLogout = resolve;
      }),
    );

    render(<LogoutButton />);
    const button = screen.getByRole("button", { name: "Log out" });

    await userEvent.click(button);
    await userEvent.click(button);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith("/api/auth/logout", { method: "POST" });
    expect(screen.getByRole("button", { name: "Signing out…" })).toBeDisabled();

    resolveLogout(new Response(JSON.stringify({ ok: true }), { status: 200 }));

    await waitFor(() => expect(window.location.assign).toHaveBeenCalledWith("/"));
  });

  it("shows an error and re-enables the button when logout fails", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response("forbidden", { status: 403 }));

    render(<LogoutButton />);
    await userEvent.click(screen.getByRole("button", { name: "Log out" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Could not log out");
    expect(screen.getByRole("button", { name: "Log out" })).toBeEnabled();
    expect(window.location.assign).not.toHaveBeenCalled();
  });
});
