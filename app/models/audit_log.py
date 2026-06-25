from enum import StrEnum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.db.base import Base


class AuditAction(StrEnum):
    USER_UPDATED = "user.updated"
    USER_DEACTIVATED = "user.deactivated"
    USER_ACTIVATED = "user.activated"
    USER_DELETED = "user.deleted"
    PASSWORD_RESET_REQUESTED = "password_reset.requested"
    PASSWORD_RESET_CONFIRMED = "password_reset.confirmed"
    TENANT_CREATED = "tenant.created"
    TENANT_ACTIVATED = "tenant.activated"
    TENANT_DEACTIVATED = "tenant.deactivated"
    BOOKING_CREATED = "booking.created"
    BOOKING_CANCELLED = "booking.cancelled"
    BOOKING_RESCHEDULED = "booking.rescheduled"
    BOOKING_CONFIRMED = "booking.confirmed"
    BOOKING_OVERRIDE_CREATED = "booking.override_created"
    BOOKING_OVERRIDE_CANCELLED = "booking.override_cancelled"
    BOOKING_HOLD_EXPIRED = "booking.hold_expired"
    BOOKING_PAYMENT_REFUNDED = "booking.payment_refunded"
    CUSTOMER_ANONYMIZED = "customer.anonymized"
    STAFF_DEACTIVATED = "staff.deactivated"
    STAFF_REACTIVATED = "staff.reactivated"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String, nullable=False, index=True)
    target_user_id = Column(Integer, nullable=True, index=True)
    target_booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=True, index=True)
    target_staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True, index=True)
    source = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
