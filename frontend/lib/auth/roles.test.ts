import { describe, expect, it } from "vitest";
import { roleIncludes } from "./roles";

describe("roleIncludes", () => {
  it("admin includes admin", () => {
    expect(roleIncludes("admin", "admin")).toBe(true);
  });

  it("platform_admin includes admin (mirrors the backend's ROLE_HIERARCHY)", () => {
    expect(roleIncludes("platform_admin", "admin")).toBe(true);
  });

  it("user does not include admin", () => {
    expect(roleIncludes("user", "admin")).toBe(false);
  });

  it("an unknown role includes nothing", () => {
    expect(roleIncludes("not-a-real-role", "admin")).toBe(false);
  });
});
