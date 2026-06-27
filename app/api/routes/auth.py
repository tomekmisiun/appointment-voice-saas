from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies.rate_limit import (
    auth_demo_rate_limit,
    auth_login_rate_limit,
    auth_logout_rate_limit,
    auth_refresh_rate_limit,
    auth_register_rate_limit,
    password_reset_rate_limit,
)
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.tenant import get_request_tenant
from app.api.openapi import AUTH_ERROR_RESPONSES, RATE_LIMITED_ERROR_RESPONSES
from app.core.config import settings
from app.core.domain_errors import NotFoundError
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import (
    LogoutRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    Token,
    UserCreate,
    UserLogin,
)
from app.schemas.user import UserRead
from app.services.auth_service import (
    create_demo_session,
    create_user,
    login_user,
    logout_user,
    rotate_refresh_token,
)
from app.services.password_reset_service import (
    confirm_password_reset,
    request_password_reset,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    summary="Register a new user",
    description="Create an active user account with the default `user` role.",
    responses={**AUTH_ERROR_RESPONSES, **RATE_LIMITED_ERROR_RESPONSES},
    dependencies=[Depends(auth_register_rate_limit())],
)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_request_tenant),
):
    if not settings.registration_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is disabled",
        )

    return create_user(db, user_data, tenant.id)


@router.post(
    "/login",
    response_model=Token,
    summary="Login and receive JWT tokens",
    description=(
        "Authenticate with email and password. Returns a short-lived access "
        "token and a refresh token used for rotation."
    ),
    responses={**AUTH_ERROR_RESPONSES, **RATE_LIMITED_ERROR_RESPONSES},
    dependencies=[Depends(auth_login_rate_limit())],
)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_request_tenant),
):
    access_token, refresh_token = login_user(db, login_data, tenant.id)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get the current user profile",
    responses=AUTH_ERROR_RESPONSES,
)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post(
    "/refresh",
    response_model=Token,
    summary="Rotate access and refresh tokens",
    description="Exchange a valid refresh token for a new access/refresh pair.",
    responses={**AUTH_ERROR_RESPONSES, **RATE_LIMITED_ERROR_RESPONSES},
    dependencies=[Depends(auth_refresh_rate_limit())],
)
def refresh_token(
    token_data: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    access_token, refresh_token = rotate_refresh_token(db, token_data.refresh_token)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout and revoke refresh token",
    description="Revokes the submitted refresh token in Redis.",
    responses={**AUTH_ERROR_RESPONSES, **RATE_LIMITED_ERROR_RESPONSES},
    dependencies=[Depends(auth_logout_rate_limit())],
)
def logout(token_data: LogoutRequest):
    logout_user(token_data.refresh_token)


@router.post(
    "/password-reset/request",
    response_model=MessageResponse,
    summary="Request a password reset email",
    description=(
        "Always returns the same success message to avoid account enumeration. "
        "Active users receive a background email job with a single-use reset "
        "token."
    ),
    responses=RATE_LIMITED_ERROR_RESPONSES,
)
async def request_reset_password(
    request: Request,
    reset_request: PasswordResetRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_request_tenant),
):
    request.scope["_json"] = {"email": str(reset_request.email)}
    password_reset_rate_limit(request)
    message = request_password_reset(db, reset_request, tenant.id)

    return MessageResponse(message=message)


@router.post(
    "/demo",
    response_model=Token,
    summary="Start a public demo session",
    description=(
        "Returns short-lived JWT tokens for the pre-configured read-only demo user. "
        "Requires PUBLIC_DEMO_ENABLED=true and correct PUBLIC_DEMO_USER_EMAIL / "
        "PUBLIC_DEMO_BUSINESS_ID configuration. "
        "The demo user cannot perform any mutation."
    ),
    responses=RATE_LIMITED_ERROR_RESPONSES,
    dependencies=[Depends(auth_demo_rate_limit())],
)
def demo_login(
    db: Session = Depends(get_db),
):
    try:
        access_token, refresh_token = create_demo_session(db)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    summary="Confirm a password reset",
    description="Set a new password using a valid, unused, unexpired reset token.",
    responses=AUTH_ERROR_RESPONSES,
)
def confirm_reset_password(
    reset_confirm: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    message = confirm_password_reset(db, reset_confirm)

    return MessageResponse(message=message)
