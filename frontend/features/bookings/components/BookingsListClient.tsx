"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import type { BusinessRead, ServiceRead, StaffRead } from "@/lib/api/types";
import { useBookingsQuery } from "../api";
import { DEFAULT_BOOKINGS_PAGE_SIZE, type BookingsFilters } from "../types";
import { buildIdNameMap, formatInBusinessTimezone } from "../utils";
import { BookingStatusBadge } from "./BookingStatusBadge";

const STATUS_OPTIONS = [
  { value: "confirmed", label: "Confirmed" },
  { value: "cancelled", label: "Cancelled" },
];

export function BookingsListClient({
  business,
  staff,
  services,
}: {
  business: BusinessRead;
  staff: StaffRead[];
  services: ServiceRead[];
}) {
  const [status, setStatus] = useState("");
  const [staffId, setStaffId] = useState("");
  const [page, setPage] = useState(1);

  const filters: BookingsFilters = {
    status: status ? (status as BookingsFilters["status"]) : undefined,
    staffId: staffId ? Number(staffId) : undefined,
    page,
    size: DEFAULT_BOOKINGS_PAGE_SIZE,
  };

  const { data: bookings, isPending, isFetching, isError, error } = useBookingsQuery(filters);

  const staffNames = buildIdNameMap(staff);
  const serviceNames = buildIdNameMap(services);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">Bookings</h1>
        {isFetching && !isPending ? (
          <span className="text-xs text-slate-400" role="status">
            Updating…
          </span>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-4">
        <div>
          <label htmlFor="status-filter" className="block text-xs font-medium text-slate-600">
            Status
          </label>
          <select
            id="status-filter"
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setPage(1);
            }}
            className="mt-1 rounded-md border border-slate-300 px-2 py-1 text-sm"
          >
            <option value="">All</option>
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="staff-filter" className="block text-xs font-medium text-slate-600">
            Staff
          </label>
          <select
            id="staff-filter"
            value={staffId}
            onChange={(event) => {
              setStaffId(event.target.value);
              setPage(1);
            }}
            className="mt-1 rounded-md border border-slate-300 px-2 py-1 text-sm"
          >
            <option value="">All staff</option>
            {staff.map((member) => (
              <option key={member.id} value={member.id}>
                {member.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isPending ? (
        <p role="status" className="text-sm text-slate-500">
          Loading bookings…
        </p>
      ) : isError ? (
        <p role="alert" className="text-sm text-red-600">
          {error instanceof Error ? error.message : "Couldn't load bookings."}
        </p>
      ) : bookings && bookings.length === 0 ? (
        <p className="text-sm text-slate-500">No bookings match these filters.</p>
      ) : (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-xs uppercase text-slate-500">
              <th scope="col" className="py-2 pr-4">
                Status
              </th>
              <th scope="col" className="py-2 pr-4">
                Customer
              </th>
              <th scope="col" className="py-2 pr-4">
                Service
              </th>
              <th scope="col" className="py-2 pr-4">
                Staff
              </th>
              <th scope="col" className="py-2 pr-4">
                Starts
              </th>
            </tr>
          </thead>
          <tbody>
            {bookings?.map((booking) => (
              <tr key={booking.id} className="border-b border-slate-100">
                <td className="py-2 pr-4">
                  <BookingStatusBadge status={booking.status} />
                </td>
                <td className="py-2 pr-4">
                  <span>Customer #{booking.customer_id}</span>
                  <span className="block text-xs text-slate-400">Name unavailable</span>
                </td>
                <td className="py-2 pr-4">
                  {serviceNames.get(booking.service_id) ?? `Service #${booking.service_id}`}
                </td>
                <td className="py-2 pr-4">
                  {booking.staff_id
                    ? staffNames.get(booking.staff_id) ?? `Staff #${booking.staff_id}`
                    : "Any available"}
                </td>
                <td className="py-2 pr-4">
                  <Link
                    href={`/dashboard/bookings/${booking.id}`}
                    className="text-blue-700 hover:underline"
                  >
                    {formatInBusinessTimezone(booking.starts_at, business.timezone)}
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="flex items-center gap-3">
        <Button
          type="button"
          variant="secondary"
          onClick={() => setPage((current) => Math.max(1, current - 1))}
          disabled={page === 1}
        >
          Previous
        </Button>
        <span className="text-sm text-slate-500">Page {page}</span>
        <Button
          type="button"
          variant="secondary"
          onClick={() => setPage((current) => current + 1)}
          disabled={!bookings || bookings.length < DEFAULT_BOOKINGS_PAGE_SIZE}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
