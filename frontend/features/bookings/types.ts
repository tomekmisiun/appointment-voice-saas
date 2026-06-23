import type { BookingRead, BookingStatus } from "@/lib/api/types";

export type { BookingRead, BookingStatus };

export interface BookingsFilters {
  status?: BookingStatus;
  staffId?: number;
  page: number;
  size: number;
}

export const DEFAULT_BOOKINGS_PAGE_SIZE = 20;
