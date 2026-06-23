import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../../tests/mocks/server";
import { CancelBookingDialog } from "./CancelBookingDialog";

const refreshMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: refreshMock }),
}));

beforeEach(() => {
  refreshMock.mockClear();
});

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("CancelBookingDialog", () => {
  it("requires opening the dialog and confirming before calling the network", async () => {
    let called = false;
    server.use(
      http.post("/api/bookings/1/cancel", () => {
        called = true;
        return HttpResponse.json({ id: 1, status: "cancelled" });
      }),
    );
    const user = userEvent.setup();
    renderWithQueryClient(<CancelBookingDialog bookingId={1} />);

    expect(called).toBe(false);

    await user.click(screen.getByRole("button", { name: "Cancel booking" }));
    expect(screen.getByText("Cancel this booking?")).toBeVisible();
    expect(called).toBe(false);
  });

  it("closing the dialog without confirming never calls the network", async () => {
    let called = false;
    server.use(
      http.post("/api/bookings/1/cancel", () => {
        called = true;
        return HttpResponse.json({ id: 1, status: "cancelled" });
      }),
    );
    const user = userEvent.setup();
    renderWithQueryClient(<CancelBookingDialog bookingId={1} />);

    await user.click(screen.getByRole("button", { name: "Cancel booking" }));
    await user.click(screen.getByRole("button", { name: "Keep booking" }));

    expect(called).toBe(false);
  });

  it("on confirm, sends the typed reason and refreshes the page on success", async () => {
    let receivedBody: { reason?: string } | null = null;
    server.use(
      http.post("/api/bookings/1/cancel", async ({ request }) => {
        receivedBody = (await request.json()) as { reason?: string };
        return HttpResponse.json({ id: 1, status: "cancelled" });
      }),
    );
    const user = userEvent.setup();
    renderWithQueryClient(<CancelBookingDialog bookingId={1} />);

    await user.click(screen.getByRole("button", { name: "Cancel booking" }));
    await user.type(screen.getByLabelText(/reason/i), "Customer requested");
    await user.click(screen.getByRole("button", { name: "Yes, cancel booking" }));

    await waitFor(() => expect(refreshMock).toHaveBeenCalled());
    expect(receivedBody).toEqual({ reason: "Customer requested" });
  });

  it("shows an inline error and does not refresh when the backend rejects the cancellation", async () => {
    server.use(
      http.post("/api/bookings/1/cancel", () =>
        HttpResponse.json({ error: { code: "conflict", message: "Already cancelled" } }, { status: 409 }),
      ),
    );
    const user = userEvent.setup();
    renderWithQueryClient(<CancelBookingDialog bookingId={1} />);

    await user.click(screen.getByRole("button", { name: "Cancel booking" }));
    await user.click(screen.getByRole("button", { name: "Yes, cancel booking" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Already cancelled");
    expect(refreshMock).not.toHaveBeenCalled();
  });
});
