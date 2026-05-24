"use client";

import { useAuthStore } from "@/stores/auth-store";
import { hasMinRole, Role } from "@/lib/permissions";

export function RoleGate({
  minRole,
  children,
  fallback = null,
}: {
  minRole: Role;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const role = useAuthStore((s) => s.role);
  if (!hasMinRole(role, minRole)) return <>{fallback}</>;
  return <>{children}</>;
}

export function useRole() {
  const role = useAuthStore((s) => s.role);
  return {
    role,
    canView: hasMinRole(role, "viewer"),
    canAnalyze: hasMinRole(role, "analyst"),
    canAdmin: hasMinRole(role, "admin"),
    isOwner: role === "owner",
  };
}
