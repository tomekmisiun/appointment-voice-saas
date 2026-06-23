/**
 * Mirrors the backend's role hierarchy exactly (app/core/permissions.py
 * ROLE_HIERARCHY, enforced via role_includes() in
 * app/api/dependencies/auth.py's require_role()). A `platform_admin` user
 * is allowed everywhere an `admin` is — checking `role === "admin"` on
 * its own would incorrectly lock that role out of an action the backend
 * actually grants it.
 */
const ROLE_HIERARCHY: Record<string, readonly string[]> = {
  platform_admin: ["platform_admin", "admin", "user"],
  admin: ["admin", "user"],
  user: ["user"],
};

export function roleIncludes(actorRole: string, requiredRole: string): boolean {
  return ROLE_HIERARCHY[actorRole]?.includes(requiredRole) ?? false;
}
