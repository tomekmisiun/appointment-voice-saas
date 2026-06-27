from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_tenant_id_email", "tenant_id", "email", unique=True),
        # Composite FK target for business_memberships (SAC-003): lets a
        # (tenant_id, user_id) foreign key enforce that a membership's user
        # actually belongs to its tenant, at the DB level.
        Index("uix_users_tenant_id_id", "tenant_id", "id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tenants.id"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String)
    hashed_password: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[str] = mapped_column(String, nullable=False, default="user")
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_demo_user: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tenant = relationship("Tenant")
    password_reset_tokens = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
