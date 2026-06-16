from dataclasses import dataclass, field

from app.models.business import Business


@dataclass
class PlanPolicy:
    """Permissive stub — all limits unset, all features enabled."""
    sms_limit: int | None = None
    ivr_minutes_limit: int | None = None
    live_transfer_enabled: bool = True
    callback_enabled: bool = True
    max_transfer_call_seconds: int | None = None
    extra: dict = field(default_factory=dict)


def get_plan_policy(business: Business) -> PlanPolicy:
    """Return the active policy for a business.

    Today this always returns the permissive defaults regardless of
    subscription_plan.  When billing enforcement is added, this function
    becomes the single seam where plan-to-limits logic lives.
    """
    return PlanPolicy()
