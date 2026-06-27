from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_non_demo_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.customer import CustomerRead
from app.services.customer_service import gdpr_delete_customer

router = APIRouter(prefix="/businesses/{business_id}/customers", tags=["customers"])


@router.post(
    "/{customer_id}/gdpr-delete",
    response_model=CustomerRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_non_demo_user)],
)
def gdpr_delete_customer_endpoint(
    business_id: int,
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return gdpr_delete_customer(
        db,
        customer_id,
        business_id,
        current_user.tenant_id,
        actor_id=current_user.id,
    )
