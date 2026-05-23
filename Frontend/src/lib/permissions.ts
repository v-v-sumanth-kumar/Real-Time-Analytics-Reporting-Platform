export type Role = "viewer" | "analyst" | "admin" | "owner";

const ROLE_RANK: Record<Role, number> = {
  viewer: 1,
  analyst: 2,
  admin: 3,
  owner: 4,
};

export function hasMinRole(userRole: Role | null | undefined, required: Role): boolean {
  // While role is loading (e.g. existing session before /me returns), show viewer routes
  if (!userRole) return required === "viewer";
  return ROLE_RANK[userRole] >= ROLE_RANK[required];
}

export function roleLabel(role: Role | null | undefined): string {
  if (!role) return "Loading…";
  return role;
}
