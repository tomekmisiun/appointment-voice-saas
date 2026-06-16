from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.ivr import IvrOptionRead, IvrSessionResponse, SimulateCallRequest, SimulatePressRequest
from app.services.ivr_service import handle_keypress, start_session

router = APIRouter(prefix="/ivr/simulate", tags=["ivr"])


@router.post("/call", response_model=IvrSessionResponse, status_code=status.HTTP_201_CREATED)
def simulate_call(
    body: SimulateCallRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    session, response = start_session(
        db,
        business_id=body.business_id,
        tenant_id=current_user.tenant_id,
        caller_phone=body.caller_phone,
    )
    _ = session
    return IvrSessionResponse(
        session_id=response.session_id,
        prompt=response.prompt,
        options=[IvrOptionRead(key=o.key, label=o.label) for o in response.options],
        action=response.action,
        transfer_destination=response.transfer_destination,
    )


@router.post("/press", response_model=IvrSessionResponse)
def simulate_press(
    body: SimulatePressRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    response = handle_keypress(
        db,
        session_id=body.session_id,
        tenant_id=current_user.tenant_id,
        key=body.key,
    )
    return IvrSessionResponse(
        session_id=response.session_id,
        prompt=response.prompt,
        options=[IvrOptionRead(key=o.key, label=o.label) for o in response.options],
        action=response.action,
        transfer_destination=response.transfer_destination,
    )
