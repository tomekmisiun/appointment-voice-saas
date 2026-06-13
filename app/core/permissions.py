from enum import StrEnum


class Permission(StrEnum):
    USERS_LIST = "users.list"
    USERS_READ = "users.read"
    USERS_READ_SELF = "users.read.self"
    USERS_UPDATE = "users.update"
    USERS_UPDATE_SELF = "users.update.self"
    USERS_DELETE = "users.delete"
    USERS_ACTIVATE = "users.activate"
    USERS_DEACTIVATE = "users.deactivate"
    ADMIN_ACCESS = "admin.access"
    AUDIT_LOGS_LIST = "audit_logs.list"
    FILES_UPLOAD = "files.upload"
    FILES_DOWNLOAD = "files.download"
    FILES_DOWNLOAD_SELF = "files.download.self"
    FILES_DELETE = "files.delete"
    FILES_DELETE_SELF = "files.delete.self"
    TENANTS_LIST = "tenants.list"
    TENANTS_PROVISION = "tenants.provision"
    TENANTS_MANAGE = "tenants.manage"


USER_PERMISSIONS = frozenset(
    {
        Permission.USERS_READ_SELF,
        Permission.USERS_UPDATE_SELF,
        Permission.FILES_UPLOAD,
        Permission.FILES_DOWNLOAD_SELF,
        Permission.FILES_DELETE_SELF,
    }
)

TENANT_ADMIN_PERMISSIONS = frozenset(
    permission
    for permission in Permission
    if not permission.value.startswith("tenants.")
)

PLATFORM_ADMIN_PERMISSIONS = frozenset(Permission)

ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "user": USER_PERMISSIONS,
    "admin": TENANT_ADMIN_PERMISSIONS,
    "platform_admin": PLATFORM_ADMIN_PERMISSIONS,
}

ROLE_HIERARCHY: dict[str, frozenset[str]] = {
    "platform_admin": frozenset({"platform_admin", "admin", "user"}),
    "admin": frozenset({"admin", "user"}),
    "user": frozenset({"user"}),
}
