from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_non_demo_user, require_permission
from app.api.openapi import ADMIN_ERROR_RESPONSES, PROTECTED_ERROR_RESPONSES
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.audit_log import AuditAction
from app.models.user import User
from app.schemas.user import UserAdminUpdate, UserListPage, UserRead, UserRole, UserSearchMode, UserSelfUpdate
from app.services.audit_log_service import create_audit_log
from app.services.permission_service import (
    can_read_user,
    can_update_user,
    user_has_permission,
)
from app.services.user_service import (
    activate_user,
    deactivate_user,
    delete_user,
    get_user_by_id,
    get_users,
    invalidate_users_list_cache,
    update_user,
)


class UserSortBy(str, Enum):
    id = "id"
    email = "email"
    role = "role"
    is_active = "is_active"


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


def user_list_items(result) -> list[UserRead]:
    items = []

    for item in result.items:
        if isinstance(item, dict):
            items.append(UserRead.model_validate(item))
        else:
            items.append(UserRead.model_validate(item))

    return items


router = APIRouter(prefix="/users", tags=["users"])


def commit_user_mutation_with_audit(
    db: Session,
    *,
    tenant_id: int,
    admin_id: int,
    action: AuditAction,
    target_user_id: int,
) -> None:
    create_audit_log(
        db=db,
        tenant_id=tenant_id,
        admin_id=admin_id,
        action=action,
        target_user_id=target_user_id,
        commit=False,
    )
    db.commit()
    invalidate_users_list_cache(tenant_id)


@router.get(
    "/",
    response_model=UserListPage,
    summary="List users",
    description=(
        "Admin-only user listing with keyset pagination, sorting, filters, and "
        "email search. Use `cursor` for scalable paging; `page` remains as a "
        "legacy offset fallback."
    ),
    responses=ADMIN_ERROR_RESPONSES,
)
def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    cursor: str | None = None,
    sort_by: UserSortBy = Query(UserSortBy.id),
    sort_order: SortOrder = Query(SortOrder.asc),
    role: UserRole | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    search_mode: UserSearchMode = Query(UserSearchMode.prefix),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USERS_LIST)),
):
    if cursor is not None and page != 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="cursor cannot be combined with page > 1",
        )

    skip = (page - 1) * size if page > 1 and cursor is None else None

    try:
        result = get_users(
            db=db,
            tenant_id=current_user.tenant_id,
            limit=size,
            sort_by=sort_by.value,
            sort_order=sort_order.value,
            role=role.value if role else None,
            is_active=is_active,
            search=search,
            search_mode=search_mode.value,
            cursor=cursor,
            skip=skip,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return UserListPage(
        items=user_list_items(result),
        next_cursor=result.next_cursor,
    )


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get a user by ID",
    description="Admins can read any user. Regular users can only read themselves.",
    responses=PROTECTED_ERROR_RESPONSES,
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = get_user_by_id(db, user_id, current_user.tenant_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not can_read_user(current_user, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    return user


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    summary="Update a user",
    description=(
        "Admins can update managed fields and activation state. Regular users "
        "can update only their own safe profile fields."
    ),
    responses=PROTECTED_ERROR_RESPONSES,
    dependencies=[Depends(require_non_demo_user)],
)
def patch_user(
    user_id: int,
    user_update: UserAdminUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = get_user_by_id(db, user_id, current_user.tenant_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not can_update_user(current_user, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    if user_has_permission(current_user, Permission.USERS_UPDATE):
        update_data = user_update
    else:
        update_data = UserSelfUpdate(**user_update.model_dump(exclude_unset=True))

    if user_has_permission(current_user, Permission.USERS_UPDATE):
        updated_user = update_user(db, user, update_data, commit=False)
        commit_user_mutation_with_audit(
            db,
            tenant_id=current_user.tenant_id,
            admin_id=current_user.id,
            action=AuditAction.USER_UPDATED,
            target_user_id=user_id,
        )
        db.refresh(updated_user)
    else:
        updated_user = update_user(db, user, update_data)

    return updated_user


@router.patch(
    "/{user_id}/deactivate",
    response_model=UserRead,
    summary="Deactivate a user",
    responses=ADMIN_ERROR_RESPONSES,
    dependencies=[Depends(require_non_demo_user)],
)
def deactivate_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USERS_DEACTIVATE)),
):
    user = deactivate_user(
        db,
        user_id,
        current_user.tenant_id,
        commit=False,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    commit_user_mutation_with_audit(
        db,
        tenant_id=current_user.tenant_id,
        admin_id=current_user.id,
        action=AuditAction.USER_DEACTIVATED,
        target_user_id=user_id,
    )
    db.refresh(user)

    return user


@router.patch(
    "/{user_id}/activate",
    response_model=UserRead,
    summary="Activate a user",
    responses=ADMIN_ERROR_RESPONSES,
    dependencies=[Depends(require_non_demo_user)],
)
def activate_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USERS_ACTIVATE)),
):
    user = activate_user(
        db,
        user_id,
        current_user.tenant_id,
        commit=False,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    commit_user_mutation_with_audit(
        db,
        tenant_id=current_user.tenant_id,
        admin_id=current_user.id,
        action=AuditAction.USER_ACTIVATED,
        target_user_id=user_id,
    )
    db.refresh(user)

    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user",
    responses=ADMIN_ERROR_RESPONSES,
    dependencies=[Depends(require_non_demo_user)],
)
def remove_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USERS_DELETE)),
):
    user = get_user_by_id(db, user_id, current_user.tenant_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    target_user_id = user_id
    delete_user(db, user, commit=False)
    commit_user_mutation_with_audit(
        db,
        tenant_id=current_user.tenant_id,
        admin_id=current_user.id,
        action=AuditAction.USER_DELETED,
        target_user_id=target_user_id,
    )
