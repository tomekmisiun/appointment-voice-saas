from types import SimpleNamespace

from app.core.permissions import Permission
from app.services.permission_service import (
    can_read_user,
    can_update_user,
    get_permissions_for_role,
    role_includes,
    user_has_permission,
)


def make_user(user_id: int, role: str, tenant_id: int = 1):
    return SimpleNamespace(id=user_id, role=role, tenant_id=tenant_id)


def test_tenant_admin_role_has_tenant_scoped_permissions_only():
    permissions = get_permissions_for_role("admin")

    assert Permission.USERS_LIST in permissions
    assert Permission.AUDIT_LOGS_LIST in permissions
    assert Permission.ADMIN_ACCESS in permissions
    assert Permission.TENANTS_PROVISION not in permissions
    assert Permission.TENANTS_LIST not in permissions
    assert Permission.TENANTS_MANAGE not in permissions


def test_platform_admin_role_has_full_permission_set():
    permissions = get_permissions_for_role("platform_admin")

    assert Permission.USERS_LIST in permissions
    assert Permission.AUDIT_LOGS_LIST in permissions
    assert Permission.ADMIN_ACCESS in permissions
    assert Permission.TENANTS_PROVISION in permissions
    assert Permission.TENANTS_LIST in permissions
    assert Permission.TENANTS_MANAGE in permissions


def test_user_role_has_self_service_permissions_only():
    permissions = get_permissions_for_role("user")

    assert Permission.USERS_READ_SELF in permissions
    assert Permission.USERS_UPDATE_SELF in permissions
    assert Permission.FILES_UPLOAD in permissions
    assert Permission.USERS_LIST not in permissions
    assert Permission.ADMIN_ACCESS not in permissions
    assert Permission.TENANTS_PROVISION not in permissions


def test_role_hierarchy_allows_admin_to_satisfy_user_role_checks():
    admin = make_user(1, "admin")

    assert role_includes(admin.role, "admin") is True
    assert role_includes(admin.role, "user") is True


def test_role_hierarchy_allows_platform_admin_to_satisfy_admin_checks():
    platform_admin = make_user(1, "platform_admin")

    assert role_includes(platform_admin.role, "platform_admin") is True
    assert role_includes(platform_admin.role, "admin") is True
    assert role_includes(platform_admin.role, "user") is True


def test_role_hierarchy_does_not_elevate_regular_users():
    user = make_user(2, "user")

    assert role_includes(user.role, "admin") is False
    assert role_includes(user.role, "user") is True


def test_can_read_user_allows_self_read_for_regular_user():
    user = make_user(3, "user")

    assert can_read_user(user, user) is True
    assert can_read_user(user, make_user(4, "user")) is False


def test_can_read_user_allows_admin_to_read_any_user_in_same_tenant():
    admin = make_user(1, "admin")
    target = make_user(99, "user", tenant_id=1)

    assert can_read_user(admin, target) is True


def test_can_read_user_denies_cross_tenant_access():
    admin = make_user(1, "admin", tenant_id=1)
    target = make_user(99, "user", tenant_id=2)

    assert can_read_user(admin, target) is False


def test_can_update_user_allows_self_update_for_regular_user():
    user = make_user(3, "user")

    assert can_update_user(user, user) is True
    assert can_update_user(user, make_user(4, "user")) is False


def test_user_has_permission_reflects_role_policy():
    admin = make_user(1, "admin")
    platform_admin = make_user(3, "platform_admin")
    user = make_user(2, "user")

    assert user_has_permission(admin, Permission.USERS_DELETE) is True
    assert user_has_permission(admin, Permission.TENANTS_PROVISION) is False
    assert user_has_permission(platform_admin, Permission.TENANTS_PROVISION) is True
    assert user_has_permission(user, Permission.USERS_DELETE) is False
