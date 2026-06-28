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

import logging
from datetime import time

from app.core.config import settings
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.business import Business, TransferDestinationPolicy
from app.models.service import Service
from app.models.staff import Staff
from app.models.user import User
from app.models.working_hours import WorkingHours
from app.services.tenant_seed_service import ensure_default_tenant

logger = logging.getLogger(__name__)

DEMO_BUSINESS_NAME = "Glamour Studio Demo"
DEMO_USER_EMAIL = "demo@voxslot.demo"

# The Twilio-provisioned inbound number clients call to reach the demo IVR.
DEMO_INBOUND_PHONE = "+18174057514"
# The owner's direct line — receives booking notification SMS.
DEMO_OWNER_NOTIFICATION_PHONE = "+48505460409"
# Where the IVR transfers calls (may equal the owner's direct line).
DEMO_TRANSFER_PHONE = "+48505460409"

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


def seed_demo_user(db, tenant_id: int) -> dict:
    """Idempotently create the public demo user.

    Email is taken from PUBLIC_DEMO_USER_EMAIL (settings.public_demo_user_email),
    falling back to DEMO_USER_EMAIL if the env var is not set. This keeps the
    seeded user in sync with the address that create_demo_session looks up.
    The password is a random placeholder — the demo session endpoint uses
    is_demo_user for lookup, not password authentication.
    """
    email = settings.public_demo_user_email or DEMO_USER_EMAIL

    existing = (
        db.query(User)
        .filter(User.email == email, User.tenant_id == tenant_id)
        .first()
    )
    if existing is not None:
        if not existing.is_demo_user:
            raise ValueError(
                f"User '{email}' already exists with is_demo_user=False. "
                f"Either change PUBLIC_DEMO_USER_EMAIL to a different address, "
                f"or manually set is_demo_user=True on the existing user."
            )
        return {"demo_user": [f"skipped: {email} (already exists)"]}

    import secrets as _secrets
    placeholder_password = hash_password(_secrets.token_urlsafe(32))
    user = User(
        tenant_id=tenant_id,
        email=email,
        hashed_password=placeholder_password,
        is_active=True,
        role="user",
        is_demo_user=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"demo_user": [f"created: {email} (id={user.id})"]}


def seed_demo(db) -> dict:
    tenant = ensure_default_tenant(db, commit=True)
    results: dict[str, list] = {"business": [], "staff": [], "services": [], "hours": []}
    demo_inbound_phone = settings.twilio_voice_number.strip() or DEMO_INBOUND_PHONE

    # ── Business ──────────────────────────────────────────────────────────────
    biz = None
    if settings.public_demo_business_id:
        biz = (
            db.query(Business)
            .filter(
                Business.tenant_id == tenant.id,
                Business.id == settings.public_demo_business_id,
            )
            .first()
        )

    if biz is None:
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
            phone=demo_inbound_phone,
            owner_notification_phone=DEMO_OWNER_NOTIFICATION_PHONE,
            transfer_phone_number=DEMO_TRANSFER_PHONE,
            is_active=True,
            transfer_enabled=True,
            transfer_destination_policy=TransferDestinationPolicy.BUSINESS_PHONE,
        )
        db.add(biz)
        db.commit()
        db.refresh(biz)
        results["business"].append(f"created: {DEMO_BUSINESS_NAME}")
    else:
        # Always sync the phone fields so re-running seed after env changes is safe.
        biz.phone = demo_inbound_phone
        biz.owner_notification_phone = DEMO_OWNER_NOTIFICATION_PHONE
        biz.transfer_phone_number = DEMO_TRANSFER_PHONE
        db.commit()
        db.refresh(biz)
        results["business"].append(f"updated: {DEMO_BUSINESS_NAME}")

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

    if settings.environment not in ("development", "production"):
        raise SystemExit("seed_demo_data only runs when ENVIRONMENT=development or production")

    logger.info("[seed] starting demo data seed")
    db = SessionLocal()
    try:
        tenant = ensure_default_tenant(db, commit=True)
        logger.info("[seed] tenant: id=%d slug=%s", tenant.id, tenant.slug)
        results = seed_demo(db)
        user_results = seed_demo_user(db, tenant.id)
        results.update(user_results)
    except ValueError as exc:
        logger.error("[seed] configuration error: %s", exc)
        db.close()
        raise SystemExit(f"[demo_user] ERROR: {exc}") from exc
    except Exception as exc:
        logger.error("[seed] unexpected error: %s: %s", type(exc).__name__, exc)
        db.close()
        raise SystemExit(f"[seed] FAILED: {type(exc).__name__}: {exc}") from exc
    finally:
        db.close()

    for section, items in results.items():
        for item in items:
            logger.info("[seed] [%s] %s", section, item)
    logger.info("[seed] done")


if __name__ == "__main__":
    main()
