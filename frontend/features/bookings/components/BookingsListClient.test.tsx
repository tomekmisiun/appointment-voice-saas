import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "../../../tests/mocks/server";
import type { BusinessRead, ServiceRead, StaffRead } from "@/lib/api/types";
import { BookingsListClient } from "./BookingsListClient";

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const business: BusinessRead = {
  id: 42,
  tenant_id: 1,
  name: "Glamour Studio",
  timezone: "Europe/Warsaw",
  phone: null,
  is_active: true,
  transfer_enabled: false,
  transfer_destination_policy: "business_phone",
  booking_mode: "internal_booking",
  external_booking_url: null,
  external_booking_label: null,
  external_booking_provider: null,
  subscription_plan: "full_booking",
  created_at: new Date().toISOString(),
};

const staff: StaffRead[] = [
  { id: 1, tenant_id: 1, business_id: 42, name: "Alice", phone: null, is_active: true, created_at: "" },
  { id: 2, tenant_id: 1, business_id: 42, name: "Bob", phone: null, is_active: true, created_at: "" },
];

const services: ServiceRead[] = [
  {
    id: 10,
    tenant_id: 1,
    business_id: 42,
    name: "Haircut",
    duration_minutes: 30,
    is_active: true,
    price_minor_units: null,
    currency: null,
    created_at: "",
  },
];

function booking(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    tenant_id: 1,
    business_id: 42,
    customer_id: 7,
    service_id: 10,
    staff_id: 1,
    starts_at: "2026-01-15T10:00:00+00:00",
    ends_at: "2026-01-15T10:30:00+00:00",
    status: "confirmed",
    source: "api",
    cancel_reason: null,
    created_at: "2026-01-10T00:00:00+00:00",
    ...overrides,
  };
}

describe("BookingsListClient", () => {
  it("shows a loading state, then the list", async () => {
    server.use(http.get("/api/bookings", () => HttpResponse.json([booking()])));

    renderWithQueryClient(<BookingsListClient business={business} staff={staff} services={services} />);

    expect(screen.getByRole("status")).toHaveTextContent(/loading/i);
    // "Alice" also appears as a <option> in the always-rendered staff
    // filter dropdown, so wait on "Haircut" instead — it only exists in
    // the table, once the query has actually resolved.
    expect(await screen.findByText("Haircut")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Alice" })).toBeInTheDocument();
    expect(screen.getByText(/Customer #7/)).toBeInTheDocument();
    expect(screen.getByText(/Name unavailable/)).toBeInTheDocument();
  });

  it("shows an empty state when there are no bookings", async () => {
    server.use(http.get("/api/bookings", () => HttpResponse.json([])));

    renderWithQueryClient(<BookingsListClient business={business} staff={staff} services={services} />);

    expect(await screen.findByText(/no bookings match/i)).toBeInTheDocument();
  });

  it("shows an error state when the proxy route fails", async () => {
    server.use(
      http.get("/api/bookings", () =>
        HttpResponse.json({ error: { code: "backend_error", message: "Backend unavailable" } }, { status: 502 }),
      ),
    );

    renderWithQueryClient(<BookingsListClient business={business} staff={staff} services={services} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Backend unavailable");
  });

  it("resolves an unknown staff/service id to a numbered fallback instead of crashing", async () => {
    server.use(
      http.get("/api/bookings", () =>
        HttpResponse.json([booking({ staff_id: 999, service_id: 888 })]),
      ),
    );

    renderWithQueryClient(<BookingsListClient business={business} staff={staff} services={services} />);

    expect(await screen.findByText("Staff #999")).toBeInTheDocument();
    expect(screen.getByText("Service #888")).toBeInTheDocument();
  });

  it("shows 'Any available' when a booking has no specific staff", async () => {
    server.use(http.get("/api/bookings", () => HttpResponse.json([booking({ staff_id: null })])));

    renderWithQueryClient(<BookingsListClient business={business} staff={staff} services={services} />);

    expect(await screen.findByText("Any available")).toBeInTheDocument();
  });

  it("re-fetches with the selected status filter and resets to page 1", async () => {
    const receivedQueries: string[] = [];
    server.use(
      http.get("/api/bookings", ({ request }) => {
        receivedQueries.push(new URL(request.url).search);
        return HttpResponse.json([booking()]);
      }),
    );
    const user = userEvent.setup();

    renderWithQueryClient(<BookingsListClient business={business} staff={staff} services={services} />);
    await screen.findByText("Alice");

    await user.selectOptions(screen.getByLabelText(/status/i), "cancelled");

    await waitFor(() => {
      expect(receivedQueries.some((q) => q.includes("status=cancelled") && q.includes("page=1"))).toBe(
        true,
      );
    });
  });

  it("Previous is disabled on page 1 and Next advances the page", async () => {
    const receivedQueries: string[] = [];
    server.use(
      http.get("/api/bookings", ({ request }) => {
        const search = new URL(request.url).search;
        receivedQueries.push(search);
        // 20 items so "Next" stays enabled (page is "full").
        const items = search.includes("page=2") ? [booking({ id: 2 })] : Array.from({ length: 20 }, (_, i) => booking({ id: i + 100 }));
        return HttpResponse.json(items);
      }),
    );
    const user = userEvent.setup();

    renderWithQueryClient(<BookingsListClient business={business} staff={staff} services={services} />);
    await screen.findByText("Alice");

    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Next" }));

    await waitFor(() => {
      expect(receivedQueries.some((q) => q.includes("page=2"))).toBe(true);
    });
    expect(within(screen.getByText("Page 2").parentElement as HTMLElement).getByText("Page 2")).toBeInTheDocument();
  });
});
