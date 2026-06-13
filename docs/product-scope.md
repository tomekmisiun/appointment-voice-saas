# Product Scope

Product bootstrap scope for **Appointment Voice SaaS**. This document describes
the intended product direction, not implemented runtime behavior.

## Target Users

- Independent barbers who miss calls while serving customers.
- Small barber shops with one to several staff members.
- Local service businesses with appointment-based services and simple schedules,
  such as salons, groomers, massage providers, and repair shops.
- Customers who prefer calling a business phone number instead of using an app.

## Problem

Local service providers lose customers when they cannot answer the phone during
appointments. A missed call often means a missed booking, especially when the
customer wants a same-day or next-day slot and calls the next available provider.

## MVP User Flow

1. A customer calls the business phone number.
2. The automated phone flow greets the customer and presents service options.
3. The customer selects a service.
4. The system offers available appointment slots based on working hours,
   staff availability, existing bookings, and exceptions.
5. The customer selects a slot and provides or confirms contact details.
6. The system creates the booking if the slot is still available.
7. The customer receives an SMS confirmation.
8. The business receives an SMS notification with booking details.
9. The business can later view or manage the booking through an API or future
   admin experience.

## Non-Goals

- No booking runtime code in the product bootstrap task.
- No database models or migrations until the core domain model task.
- No Twilio, SMS provider, Google Calendar, AI voice agent, or frontend in the
  bootstrap phase.
- No natural-language conversation in the MVP.
- No payments, subscriptions, deposits, coupons, or billing workflows.
- No complex resource scheduling, rooms, equipment, packages, or multi-location
  chains in the MVP.
- No marketplace or consumer discovery product.

## Business Assumptions

- The first vertical is barbers or barber-like local service businesses.
- The buyer values saved bookings more than advanced scheduling customization.
- A simple phone-first flow is acceptable for the first pilot.
- SMS confirmation to both parties is enough for MVP trust.
- Staff schedules and service durations are relatively stable week to week.
- Businesses can manage setup through API/admin operations before a frontend
  exists.

## Technical Assumptions

- Existing FastAPI template capabilities remain the foundation: auth, tenants,
  users, workers, Redis, PostgreSQL, observability, Docker, and CI checks.
- Each business is tenant-scoped and must not share product data with another
  tenant.
- Booking correctness depends on database transactions and constraints, not only
  application-side availability checks.
- Voice, SMS, and calendar providers will be integrated through adapter
  boundaries after core domain logic exists.
- Timezone handling is required from the first booking implementation.
- The MVP can start with API/admin workflows before a frontend is built.
