from datetime import time

from sqlalchemy.orm import Session

from app.core.domain_errors import ConflictError, NotFoundError
from app.models.recurring_staff_block import RecurringStaffBlock
from app.services.business_service import require_business
from app.services.staff_service import require_staff_in_business


def _ensure_no_conflicting_block(
    db: Session,
    *,
    business_id: int,
    tenant_id: int,
    staff_id: int | None,
    day_of_week: int,
    start_time: time,
    end_time: time,
) -> None:
    """Reject a new recurring block whose time window overlaps an existing
    one for the exact same (business_id, staff_id, day_of_week) scope --
    mirrors P3-004's `AvailabilityException` overlap validation. Multiple
    non-overlapping blocks per scope/day are allowed (e.g. a lunch break
    and a separate afternoon break)."""
    staff_filter = (
        RecurringStaffBlock.staff_id.is_(None)
        if staff_id is None
        else RecurringStaffBlock.staff_id == staff_id
    )
    existing = (
        db.query(RecurringStaffBlock)
        .filter(
            RecurringStaffBlock.business_id == business_id,
            RecurringStaffBlock.tenant_id == tenant_id,
            staff_filter,
            RecurringStaffBlock.day_of_week == day_of_week,
        )
        .all()
    )
    for block in existing:
        if block.start_time < end_time and block.end_time > start_time:
            raise ConflictError(
                "This recurring block's time window overlaps with an existing "
                "one for the same business/staff/day of week"
            )


def create_recurring_staff_block(
    db: Session,
    *,
    tenant_id: int,
    business_id: int,
    staff_id: int | None,
    day_of_week: int,
    start_time: time,
    end_time: time,
    reason: str | None,
) -> RecurringStaffBlock:
    require_business(db, business_id, tenant_id)
    if staff_id is not None:
        require_staff_in_business(db, staff_id, business_id, tenant_id)
    _ensure_no_conflicting_block(
        db,
        business_id=business_id,
        tenant_id=tenant_id,
        staff_id=staff_id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
    )
    block = RecurringStaffBlock(
        tenant_id=tenant_id,
        business_id=business_id,
        staff_id=staff_id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        reason=reason,
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return block


def get_recurring_staff_block(
    db: Session, block_id: int, tenant_id: int
) -> RecurringStaffBlock | None:
    return (
        db.query(RecurringStaffBlock)
        .filter(
            RecurringStaffBlock.id == block_id,
            RecurringStaffBlock.tenant_id == tenant_id,
        )
        .first()
    )


def require_recurring_staff_block(
    db: Session, block_id: int, tenant_id: int
) -> RecurringStaffBlock:
    block = get_recurring_staff_block(db, block_id, tenant_id)
    if block is None:
        raise NotFoundError("Recurring staff block not found")
    return block


def require_recurring_staff_block_in_business(
    db: Session, block_id: int, business_id: int, tenant_id: int
) -> RecurringStaffBlock:
    """Like require_recurring_staff_block(), but also rejects a block that
    belongs to a different business within the same tenant. Built in from
    the start, unlike working_hours/availability_exceptions originally
    were (see AVS-TD-029/AVS-TD-032)."""
    block = require_recurring_staff_block(db, block_id, tenant_id)
    if block.business_id != business_id:
        raise NotFoundError("Recurring staff block not found")
    return block


def list_recurring_staff_blocks(
    db: Session,
    business_id: int,
    tenant_id: int,
    *,
    staff_id: int | None = None,
    day_of_week: int | None = None,
) -> list[RecurringStaffBlock]:
    query = db.query(RecurringStaffBlock).filter(
        RecurringStaffBlock.business_id == business_id,
        RecurringStaffBlock.tenant_id == tenant_id,
    )
    if staff_id is not None:
        query = query.filter(RecurringStaffBlock.staff_id == staff_id)
    if day_of_week is not None:
        query = query.filter(RecurringStaffBlock.day_of_week == day_of_week)
    return query.order_by(
        RecurringStaffBlock.day_of_week.asc(), RecurringStaffBlock.start_time.asc()
    ).all()


def delete_recurring_staff_block(
    db: Session, block_id: int, tenant_id: int, *, business_id: int
) -> None:
    block = require_recurring_staff_block_in_business(db, block_id, business_id, tenant_id)
    db.delete(block)
    db.commit()
