export interface NavItem {
  label: string;
  href: string;
  /** Only modules with a real page ship as "active" — every other module ships in its own later branch. */
  status: "active" | "coming-soon";
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Overview", href: "/dashboard", status: "active" },
  { label: "Bookings", href: "/dashboard/bookings", status: "active" },
  { label: "Calendar", href: "/dashboard/calendar", status: "coming-soon" },
  { label: "Clients", href: "/dashboard/clients", status: "coming-soon" },
  { label: "Staff", href: "/dashboard/staff", status: "active" },
  { label: "Services", href: "/dashboard/services", status: "coming-soon" },
  { label: "Availability", href: "/dashboard/availability", status: "coming-soon" },
  { label: "Waitlist", href: "/dashboard/waitlist", status: "coming-soon" },
  { label: "Voice & IVR", href: "/dashboard/voice", status: "coming-soon" },
  { label: "Notifications", href: "/dashboard/notifications", status: "coming-soon" },
  { label: "Settings", href: "/dashboard/settings", status: "coming-soon" },
];
