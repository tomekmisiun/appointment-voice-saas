"""Demo seed for AVS-J001.

Creates a deterministic demo scenario:
  - 1 business ("Glamour Studio Demo")
  - 3 staff members with phones (for IVR transfer)
  - 3 services (Haircut, Coloring, Manicure)
  - Working hours: Mon–Fri 09:00–17:00, Sat 10:00–14:00
  - Business transfer enabled → business_phone policy

All fake providers (SMS, calendar) are configured via environment variables;
no provider objects need to be seeded here.
"""

from datetime import time

from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.models.business import Business, TransferDestinationPolicy
from app.models.service import Service
from app.models.staff import Staff
from app.models.working_hours import WorkingHours
from app.services.tenant_seed_service import ensure_default_tenant

DEMO_BUSINESS_NAME = "Glamour Studio Demo"

# Mon=0 … Fri=4, Sat=5
WEEKDAY_HOURS = [(d, time(9, 0), time(17, 0)) for d in range(5)]
SATURDAY_HOURS = [(5, time(10, 0), time(14, 0))]
ALL_HOURS = WEEKDAY_HOURS + SATURDAY_HOURS

DEMO_STAFF = [
    {"name": "Anna Kowalska", "phone": "+48100200301"},
    {"name": "Bartek Nowak", "phone": "+48100200302"},
    {"name": "Celina Wiśniewska", "phone": "+48100200303"},
]

DEMO_SERVICES = [
    {"name": "Haircut", "duration_minutes": 30, "price_minor_units": 5000, "currency": "PLN"},
    {"name": "Coloring", "duration_minutes": 90, "price_minor_units": 15000, "currency": "PLN"},
    {"name": "Manicure", "duration_minutes": 45, "price_minor_units": 7000, "currency": "PLN"},
]


def seed_demo(db) -> dict:
    tenant = ensure_default_tenant(db, commit=True)
    results: dict[str, list] = {"business": [], "staff": [], "services": [], "hours": []}

    # ── Business ──────────────────────────────────────────────────────────────
    biz = (
        db.query(Business)
        .filter(Business.tenant_id == tenant.id, Business.name == DEMO_BUSINESS_NAME)
        .first()
    )
    if biz is None:
        biz = Business(
            tenant_id=tenant.id,
            name=DEMO_BUSINESS_NAME,
            timezone="Europe/Warsaw",
            phone="+48100200300",
            is_active=True,
            transfer_enabled=True,
            transfer_destination_policy=TransferDestinationPolicy.BUSINESS_PHONE,
        )
        db.add(biz)
        db.commit()
        db.refresh(biz)
        results["business"].append(f"created: {DEMO_BUSINESS_NAME}")
    else:
        results["business"].append(f"skipped: {DEMO_BUSINESS_NAME}")

    # ── Staff ─────────────────────────────────────────────────────────────────
    existing_names = {s.name for s in db.query(Staff).filter(Staff.business_id == biz.id).all()}
    for s in DEMO_STAFF:
        if s["name"] in existing_names:
            results["staff"].append(f"skipped: {s['name']}")
            continue
        db.add(Staff(
            tenant_id=tenant.id,
            business_id=biz.id,
            name=s["name"],
            phone=s["phone"],
            is_active=True,
        ))
        results["staff"].append(f"created: {s['name']}")
    db.commit()

    # ── Services ──────────────────────────────────────────────────────────────
    existing_svc = {s.name for s in db.query(Service).filter(Service.business_id == biz.id).all()}
    for svc in DEMO_SERVICES:
        if svc["name"] in existing_svc:
            results["services"].append(f"skipped: {svc['name']}")
            continue
        db.add(Service(
            tenant_id=tenant.id,
            business_id=biz.id,
            name=svc["name"],
            duration_minutes=svc["duration_minutes"],
            price_minor_units=svc["price_minor_units"],
            currency=svc["currency"],
            is_active=True,
        ))
        results["services"].append(f"created: {svc['name']}")
    db.commit()

    # ── Working hours (business-level, staff_id=None) ─────────────────────────
    existing_wh = {
        wh.day_of_week
        for wh in db.query(WorkingHours)
        .filter(WorkingHours.business_id == biz.id, WorkingHours.staff_id.is_(None))
        .all()
    }
    for day, start, end in ALL_HOURS:
        if day in existing_wh:
            results["hours"].append(f"skipped: day {day}")
            continue
        db.add(WorkingHours(
            tenant_id=tenant.id,
            business_id=biz.id,
            staff_id=None,
            day_of_week=day,
            start_time=start,
            end_time=end,
        ))
        results["hours"].append(f"created: day {day}")
    db.commit()

    return results


def main() -> None:
    configure_logging()

    if settings.environment != "development":
        raise SystemExit("seed_demo_data only runs when ENVIRONMENT=development")

    db = SessionLocal()
    try:
        results = seed_demo(db)
    finally:
        db.close()

    for section, items in results.items():
        for item in items:
            print(f"[{section}] {item}")


if __name__ == "__main__":
    main()
