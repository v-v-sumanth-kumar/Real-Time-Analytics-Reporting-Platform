"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Bell, Key, LayoutDashboard, LogOut, Radio, Users } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";
import { Button } from "@/components/ui/button";
import { hasMinRole, roleLabel } from "@/lib/permissions";

const links = [
  { href: "/dashboard", label: "Dashboards", icon: LayoutDashboard, minRole: "viewer" as const },
  { href: "/events", label: "Live Events", icon: Radio, minRole: "viewer" as const },
  { href: "/alerts", label: "Alerts", icon: Bell, minRole: "viewer" as const },
  { href: "/ingest", label: "Ingest", icon: BarChart3, minRole: "analyst" as const },
  { href: "/api-keys", label: "API Keys", icon: Key, minRole: "admin" as const },
  { href: "/team", label: "Team", icon: Users, minRole: "admin" as const },
];

export function Sidebar() {
  const pathname = usePathname();
  const { organization, logout, user, role } = useAuthStore();

  const visibleLinks = links.filter((l) => hasMinRole(role, l.minRole));

  return (
    <aside className="flex h-screen w-64 flex-col border-r border-border bg-card">
      <div className="border-b border-border p-6">
        <h1 className="text-lg font-bold text-primary">Analytics</h1>
        <p className="mt-1 truncate text-xs text-muted-foreground">{organization?.name}</p>
        <p className="mt-2 inline-flex rounded-full bg-primary/10 px-2 py-0.5 text-xs capitalize text-primary">
          {roleLabel(role)}
        </p>
      </div>
      <nav className="flex-1 space-y-1 p-4">
        {visibleLinks.length === 0 ? (
          <p className="px-3 text-xs text-muted-foreground">Loading navigation…</p>
        ) : (
          visibleLinks.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                pathname.startsWith(href)
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          ))
        )}
      </nav>
      <div className="border-t border-border p-4">
        <p className="mb-1 truncate text-xs text-muted-foreground">{user?.email}</p>
        <p className="mb-3 text-[10px] leading-relaxed text-muted-foreground">
          Ingest: Analyst+ · API Keys & Team: Admin+
        </p>
        <Button variant="ghost" size="sm" className="w-full justify-start" onClick={() => logout()}>
          <LogOut className="mr-2 h-4 w-4" />
          Logout
        </Button>
      </div>
    </aside>
  );
}
