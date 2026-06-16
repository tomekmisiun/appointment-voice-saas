"""Tests for AVS-J001: demo seed creates deterministic scenario."""
import pytest

from app.models.business import Business
from app.models.service import Service
from app.models.staff import Staff
from app.models.working_hours import WorkingHours
from app.seed_demo_data import DEMO_BUSINESS_NAME, seed_demo


@pytest.fixture()
def seeded(db):
    results = seed_demo(db)
    biz = (
        db.query(Business)
        .filter(Business.name == DEMO_BUSINESS_NAME)
        .first()
    )
    return {"results": results, "biz": biz, "db": db}


def test_seed_creates_business(seeded):
    assert seeded["biz"] is not None
    assert seeded["biz"].is_active is True
    assert seeded["biz"].timezone == "Europe/Warsaw"


def test_business_transfer_enabled(seeded):
    biz = seeded["biz"]
    assert biz.transfer_enabled is True
    assert biz.phone == "+48100200300"


def test_seed_creates_three_staff(seeded, db):
    biz = seeded["biz"]
    staff = db.query(Staff).filter(Staff.business_id == biz.id).all()
    assert len(staff) == 3
    assert all(s.is_active for s in staff)
    assert all(s.phone is not None for s in staff)


def test_seed_creates_three_services(seeded, db):
    biz = seeded["biz"]
    services = db.query(Service).filter(Service.business_id == biz.id).all()
    assert len(services) == 3
    names = {s.name for s in services}
    assert {"Haircut", "Coloring", "Manicure"} == names


def test_seed_creates_working_hours_mon_to_sat(seeded, db):
    biz = seeded["biz"]
    wh = (
        db.query(WorkingHours)
        .filter(WorkingHours.business_id == biz.id, WorkingHours.staff_id.is_(None))
        .all()
    )
    days = {w.day_of_week for w in wh}
    assert days == {0, 1, 2, 3, 4, 5}


def test_seed_is_idempotent(seeded, db):
    biz = seeded["biz"]
    # run again
    seed_demo(db)
    count_biz = db.query(Business).filter(Business.name == DEMO_BUSINESS_NAME).count()
    count_staff = db.query(Staff).filter(Staff.business_id == biz.id).count()
    count_svc = db.query(Service).filter(Service.business_id == biz.id).count()
    assert count_biz == 1
    assert count_staff == 3
    assert count_svc == 3
