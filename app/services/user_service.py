import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.cache import (
    get_cache_version,
    get_json_cache,
    increment_cache_version,
    set_json_cache,
)
from app.core.config import settings
from app.core.keyset_pagination import decode_cursor, encode_cursor
from app.models.user import User
from app.schemas.user import UserAdminUpdate, UserRead, UserSelfUpdate, UserSearchMode
from app.services.tenant_service import build_tenant_cache_prefix


USERS_LIST_CACHE_NAMESPACE = "users:list:v1"
USERS_LIST_CACHE_VERSION_SUFFIX = "users:list:version"


@dataclass(frozen=True)
class UserListResult:
    items: list[User] | list[dict]
    next_cursor: str | None


def build_users_list_cache_version_key(tenant_id: int) -> str:
    return f"{build_tenant_cache_prefix(tenant_id)}:{USERS_LIST_CACHE_VERSION_SUFFIX}"


def _escape_like_pattern(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def _apply_email_search_filter(query, search: str, search_mode: str):
    escaped_search = _escape_like_pattern(search)

    if search_mode == UserSearchMode.contains.value:
        return query.filter(User.email.ilike(f"%{escaped_search}%", escape="\\"))

    return query.filter(User.email.ilike(f"{escaped_search}%", escape="\\"))


def _apply_keyset_filter(
    query,
    *,
    sort_column,
    sort_order: str,
    cursor_id: int,
    cursor_sort_value,
):
    if sort_order == "desc":
        return query.filter(
            or_(
                sort_column < cursor_sort_value,
                and_(sort_column == cursor_sort_value, User.id < cursor_id),
            )
        )

    return query.filter(
        or_(
            sort_column > cursor_sort_value,
            and_(sort_column == cursor_sort_value, User.id > cursor_id),
        )
    )


def _serialize_user(user: User) -> dict:
    return UserRead.model_validate(user).model_dump(mode="json")


def _build_next_cursor(
    users: list[User],
    *,
    limit: int,
    sort_by: str,
    sort_order: str,
    role: str | None,
    is_active: bool | None,
    search: str | None,
    search_mode: str,
) -> str | None:
    if len(users) < limit:
        return None

    last_user = users[-1]
    sort_value = getattr(last_user, sort_by)

    return encode_cursor(
        {
            "id": last_user.id,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "sort_value": sort_value,
            "role": role,
            "is_active": is_active,
            "search": search,
            "search_mode": search_mode,
        }
    )


def _validate_cursor_filters(
    cursor_payload: dict,
    *,
    sort_by: str,
    sort_order: str,
    role: str | None,
    is_active: bool | None,
    search: str | None,
    search_mode: str,
) -> tuple[int, object]:
    if cursor_payload.get("sort_by") != sort_by:
        raise ValueError("cursor sort_by mismatch")

    if cursor_payload.get("sort_order") != sort_order:
        raise ValueError("cursor sort_order mismatch")

    if cursor_payload.get("role") != role:
        raise ValueError("cursor role mismatch")

    if cursor_payload.get("is_active") != is_active:
        raise ValueError("cursor is_active mismatch")

    if cursor_payload.get("search") != search:
        raise ValueError("cursor search mismatch")

    if cursor_payload.get("search_mode") != search_mode:
        raise ValueError("cursor search_mode mismatch")

    cursor_id = cursor_payload.get("id")
    cursor_sort_value = cursor_payload.get("sort_value")

    if not isinstance(cursor_id, int) or cursor_sort_value is None:
        raise ValueError("invalid cursor payload")

    return cursor_id, cursor_sort_value


def get_users(
    db: Session,
    tenant_id: int,
    *,
    limit: int,
    sort_by: str = "id",
    sort_order: str = "asc",
    role: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    search_mode: str = UserSearchMode.prefix.value,
    cursor: str | None = None,
    skip: int | None = None,
) -> UserListResult:
    use_offset = skip is not None and skip > 0

    cache_key = build_users_list_cache_key(
        tenant_id=tenant_id,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        role=role,
        is_active=is_active,
        search=search,
        search_mode=search_mode,
        cursor=cursor,
        skip=skip if use_offset else None,
    )

    if settings.users_cache_enabled:
        cached_users = get_json_cache(cache_key)

        if cached_users is not None:
            return UserListResult(
                items=cached_users["items"],
                next_cursor=cached_users.get("next_cursor"),
            )

    allowed_sort_fields = {
        "id": User.id,
        "email": User.email,
        "role": User.role,
        "is_active": User.is_active,
    }

    query = db.query(User).filter(User.tenant_id == tenant_id)

    if role is not None:
        query = query.filter(User.role == role)

    if is_active is None:
        query = query.filter(User.is_active.is_(True))
    else:
        query = query.filter(User.is_active == is_active)

    if search is not None:
        query = _apply_email_search_filter(query, search, search_mode)

    sort_column = allowed_sort_fields.get(sort_by, User.id)
    id_sort = User.id.asc() if sort_order == "asc" else User.id.desc()

    next_cursor: str | None = None

    if use_offset:
        if sort_order == "desc":
            sort_column = sort_column.desc()
        else:
            sort_column = sort_column.asc()

        users = (
            query.order_by(sort_column, id_sort)
            .offset(skip)
            .limit(limit)
            .all()
        )
    else:
        if cursor is not None:
            cursor_payload = decode_cursor(cursor)
            cursor_id, cursor_sort_value = _validate_cursor_filters(
                cursor_payload,
                sort_by=sort_by,
                sort_order=sort_order,
                role=role,
                is_active=is_active,
                search=search,
                search_mode=search_mode,
            )
            query = _apply_keyset_filter(
                query,
                sort_column=sort_column,
                sort_order=sort_order,
                cursor_id=cursor_id,
                cursor_sort_value=cursor_sort_value,
            )

        if sort_order == "desc":
            sort_column = sort_column.desc()
        else:
            sort_column = sort_column.asc()

        users = (
            query.order_by(sort_column, id_sort)
            .limit(limit)
            .all()
        )
        next_cursor = _build_next_cursor(
            users,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            role=role,
            is_active=is_active,
            search=search,
            search_mode=search_mode,
        )

    if settings.users_cache_enabled:
        set_json_cache(
            cache_key,
            {
                "items": [_serialize_user(user) for user in users],
                "next_cursor": next_cursor,
            },
            ttl_seconds=settings.users_cache_ttl_seconds,
        )

    return UserListResult(items=users, next_cursor=next_cursor)


def build_users_list_cache_key(
    *,
    tenant_id: int,
    limit: int,
    sort_by: str,
    sort_order: str,
    role: str | None,
    is_active: bool | None,
    search: str | None,
    search_mode: str,
    cursor: str | None,
    skip: int | None,
) -> str:
    cache_params = {
        "limit": limit,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "role": role,
        "is_active": is_active,
        "search": search,
        "search_mode": search_mode,
        "cursor": cursor,
        "skip": skip,
    }
    cache_hash = hashlib.sha256(
        json.dumps(cache_params, sort_keys=True).encode("utf-8")
    ).hexdigest()
    cache_version = get_cache_version(build_users_list_cache_version_key(tenant_id))

    return (
        f"{build_tenant_cache_prefix(tenant_id)}:"
        f"{USERS_LIST_CACHE_NAMESPACE}:v{cache_version}:{cache_hash}"
    )


def invalidate_users_list_cache(tenant_id: int) -> None:
    increment_cache_version(build_users_list_cache_version_key(tenant_id))


def increment_user_token_version(db: Session, user: User) -> User:
    user.token_version += 1
    db.commit()
    db.refresh(user)
    invalidate_users_list_cache(user.tenant_id)
    return user


def get_user_by_id(db: Session, user_id: int, tenant_id: int) -> User | None:
    return (
        db.query(User)
        .filter(User.id == user_id, User.tenant_id == tenant_id)
        .first()
    )


def update_user(
    db: Session,
    user: User,
    user_update: UserAdminUpdate | UserSelfUpdate,
    *,
    commit: bool = True,
) -> User:
    update_data = user_update.model_dump(exclude_unset=True)
    should_invalidate_tokens = (
        "role" in update_data and update_data["role"] != user.role
    )

    for field, value in update_data.items():
        setattr(user, field, value)

    if should_invalidate_tokens:
        user.token_version += 1

    if commit:
        db.commit()
        db.refresh(user)
        invalidate_users_list_cache(user.tenant_id)
    else:
        db.flush()

    return user


def delete_user(db: Session, user: User, *, commit: bool = True) -> None:
    tenant_id = user.tenant_id
    db.delete(user)

    if commit:
        db.commit()
        invalidate_users_list_cache(tenant_id)
    else:
        db.flush()


def deactivate_user(
    db: Session,
    user_id: int,
    tenant_id: int,
    *,
    commit: bool = True,
) -> User | None:
    user = get_user_by_id(db, user_id, tenant_id)

    if not user:
        return None

    user.is_active = False
    user.token_version += 1

    if commit:
        db.commit()
        db.refresh(user)
        invalidate_users_list_cache(tenant_id)
    else:
        db.flush()

    return user


def activate_user(
    db: Session,
    user_id: int,
    tenant_id: int,
    *,
    commit: bool = True,
) -> User | None:
    user = get_user_by_id(db, user_id, tenant_id)

    if not user:
        return None

    user.is_active = True

    if commit:
        db.commit()
        db.refresh(user)
        invalidate_users_list_cache(tenant_id)
    else:
        db.flush()

    return user
