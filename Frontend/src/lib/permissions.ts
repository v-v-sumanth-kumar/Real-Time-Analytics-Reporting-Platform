export type Role = "viewer" | "analyst" | "admin" | "owner";

const ROLE_RANK: Record<Role, number> = {
  viewer: 1,
  analyst: 2,
  admin: 3,
  owner: 4,
};

export function hasMinRole(userRole: Role | null | undefined, required: Role): boolean {
  if (!userRole) return false;
  return ROLE_RANK[userRole] >= ROLE_RANK[required];
}
