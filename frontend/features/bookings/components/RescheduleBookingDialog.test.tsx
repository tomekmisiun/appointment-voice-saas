import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../../tests/mocks/server";
import { RescheduleBookingDialog } from "./RescheduleBookingDialog";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

beforeEach(() => {
  pushMock.mockClear();
});

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("RescheduleBookingDialog", () => {
  it("does not fetch availability before the dialog is opened", async () => {
    // Regression test for a cross-provider review finding: this query
    // must not run the moment the detail page mounts (wasted request on
    // every eligible page view, and risks showing stale slots by the
    // time the admin actually opens the dialog) — see useAvailabilityQuery
    // and the `enabled: isOpen` wiring in this component.
    let backendCalled = false;
    server.use(
      http.get("/api/availability", () => {
        backendCalled = true;
        return HttpResponse.json([]);
      }),
    );
    renderWithQueryClient(
      <RescheduleBookingDialog bookingId={1} serviceId={10} staffId={2} timezone="UTC" />,
    );

    expect(backendCalled).toBe(false);
  });

  it("fetches availability for the booking's own service/staff when opened", async () => {
    let receivedQuery: string | null = null;
    server.use(
      http.get("/api/availability", ({ request }) => {
        receivedQuery = new URL(request.url).search;
        return HttpResponse.json([
          { starts_at: "2026-01-15T09:00:00Z", ends_at: "2026-01-15T09:30:00Z" },
        ]);
      }),
    );
    const user = userEvent.setup();
    renderWithQueryClient(
      <RescheduleBookingDialog bookingId={1} serviceId={10} staffId={2} timezone="UTC" />,
    );

    await user.click(screen.getByRole("button", { name: "Reschedule" }));

    await waitFor(() => expect(receivedQuery).toContain("service_id=10"));
    expect(receivedQuery).toContain("staff_id=2");
  });

  it("shows a no-availability message when there are no slots", async () => {
    server.use(http.get("/api/availability", () => HttpResponse.json([])));
    const user = userEvent.setup();
    renderWithQueryClient(
      <RescheduleBookingDialog bookingId={1} serviceId={10} staffId={null} timezone="UTC" />,
    );

    await user.click(screen.getByRole("button", { name: "Reschedule" }));

    expect(await screen.findByText(/no available times/i)).toBeInTheDocument();
  });

  it("requires selecting a slot before the confirm button is enabled", async () => {
    server.use(
      http.get("/api/availability", () =>
        HttpResponse.json([
          { starts_at: "2026-01-15T09:00:00Z", ends_at: "2026-01-15T09:30:00Z" },
        ]),
      ),
    );
    const user = userEvent.setup();
    renderWithQueryClient(
      <RescheduleBookingDialog bookingId={1} serviceId={10} staffId={null} timezone="UTC" />,
    );

    await user.click(screen.getByRole("button", { name: "Reschedule" }));
    const confirmButton = await screen.findByRole("button", { name: "Confirm new time" });
    expect(confirmButton).toBeDisabled();

    await user.click(screen.getByRole("radio"));
    expect(confirmButton).toBeEnabled();
  });

  it("re-fetches fresh availability every time the dialog is reopened, even for the same date", async () => {
    let callCount = 0;
    server.use(
      http.get("/api/availability", () => {
        callCount += 1;
        return HttpResponse.json([
          { starts_at: "2026-01-15T09:00:00Z", ends_at: "2026-01-15T09:30:00Z" },
        ]);
      }),
    );
    const user = userEvent.setup();
    renderWithQueryClient(
      <RescheduleBookingDialog bookingId={1} serviceId={10} staffId={null} timezone="UTC" />,
    );

    await user.click(screen.getByRole("button", { name: "Reschedule" }));
    await waitFor(() => expect(callCount).toBe(1));
    await user.click(screen.getByRole("button", { name: "Close" }));

    await user.click(screen.getByRole("button", { name: "Reschedule" }));
    await waitFor(() => expect(callCount).toBe(2));
  });

  it("never leaves a previously fetched slot selectable while a reopen's refetch is still in flight", async () => {
    // Regression test for a second cross-provider review finding:
    // staleTime: 0 only starts a background refetch on reopen — it
    // doesn't clear the previous response, so without gating on
    // isFetching too, the old slot stayed rendered and clickable until
    // the fresh one arrived.
    // Plain `let` + reassignment-in-closure doesn't narrow the way TS
    // expects across the async boundary (the assignment inside the MSW
    // handler isn't visible to the outer function's control-flow
    // analysis, so a direct `let` ends up typed `null` at the call site
    // below) — an object property avoids that false narrowing.
    const deferred: { resolveSecondFetch: (() => void) | null } = { resolveSecondFetch: null };
    let fetchCount = 0;
    server.use(
      http.get("/api/availability", async () => {
        fetchCount += 1;
        if (fetchCount === 2) {
          await new Promise<void>((resolve) => {
            deferred.resolveSecondFetch = resolve;
          });
          return HttpResponse.json([
            { starts_at: "2026-01-15T11:00:00Z", ends_at: "2026-01-15T11:30:00Z" },
          ]);
        }
        return HttpResponse.json([
          { starts_at: "2026-01-15T09:00:00Z", ends_at: "2026-01-15T09:30:00Z" },
        ]);
      }),
    );
    const user = userEvent.setup();
    renderWithQueryClient(
      <RescheduleBookingDialog bookingId={1} serviceId={10} staffId={null} timezone="UTC" />,
    );

    await user.click(screen.getByRole("button", { name: "Reschedule" }));
    await screen.findByRole("radio");
    await user.click(screen.getByRole("button", { name: "Close" }));

    await user.click(screen.getByRole("button", { name: "Reschedule" }));
    await waitFor(() => expect(fetchCount).toBe(2));
    // The second fetch is deliberately stuck mid-flight here — the old
    // slot from the first fetch must not still be on screen/selectable.
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/loading/i);

    deferred.resolveSecondFetch?.();
    await screen.findByRole("radio");
  });

  it("on confirm, sends the selected slot and navigates to the new booking's id", async () => {
    let receivedBody: { new_starts_at?: string } | null = null;
    server.use(
      http.get("/api/availability", () =>
        HttpResponse.json([
          { starts_at: "2026-01-15T09:00:00Z", ends_at: "2026-01-15T09:30:00Z" },
        ]),
      ),
      http.post("/api/bookings/1/reschedule", async ({ request }) => {
        receivedBody = (await request.json()) as { new_starts_at?: string };
        return HttpResponse.json({ id: 99, status: "confirmed" });
      }),
    );
    const user = userEvent.setup();
    renderWithQueryClient(
      <RescheduleBookingDialog bookingId={1} serviceId={10} staffId={null} timezone="UTC" />,
    );

    await user.click(screen.getByRole("button", { name: "Reschedule" }));
    await user.click(await screen.findByRole("radio"));
    await user.click(screen.getByRole("button", { name: "Confirm new time" }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/dashboard/bookings/99"));
    expect(receivedBody).toEqual({ new_starts_at: "2026-01-15T09:00:00Z" });
  });

  it("shows an inline error and does not navigate when the backend rejects the reschedule", async () => {
    server.use(
      http.get("/api/availability", () =>
        HttpResponse.json([
          { starts_at: "2026-01-15T09:00:00Z", ends_at: "2026-01-15T09:30:00Z" },
        ]),
      ),
      http.post("/api/bookings/1/reschedule", () =>
        HttpResponse.json({ error: { code: "conflict", message: "Slot no longer available" } }, { status: 409 }),
      ),
    );
    const user = userEvent.setup();
    renderWithQueryClient(
      <RescheduleBookingDialog bookingId={1} serviceId={10} staffId={null} timezone="UTC" />,
    );

    await user.click(screen.getByRole("button", { name: "Reschedule" }));
    await user.click(await screen.findByRole("radio"));
    await user.click(screen.getByRole("button", { name: "Confirm new time" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Slot no longer available");
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("re-fetches availability and clears the selected slot when the date changes", async () => {
    const receivedDates: string[] = [];
    server.use(
      http.get("/api/availability", ({ request }) => {
        const date = new URL(request.url).searchParams.get("date");
        if (date) receivedDates.push(date);
        return HttpResponse.json([
          { starts_at: "2026-01-15T09:00:00Z", ends_at: "2026-01-15T09:30:00Z" },
        ]);
      }),
    );
    const user = userEvent.setup();
    renderWithQueryClient(
      <RescheduleBookingDialog bookingId={1} serviceId={10} staffId={null} timezone="UTC" />,
    );

    await user.click(screen.getByRole("button", { name: "Reschedule" }));
    await user.click(await screen.findByRole("radio"));

    const dateInput = screen.getByLabelText(/new date/i);
    await user.clear(dateInput);
    await user.type(dateInput, "2026-02-01");

    await waitFor(() => expect(receivedDates).toContain("2026-02-01"));
    expect(screen.getByRole("button", { name: "Confirm new time" })).toBeDisabled();
  });
});
