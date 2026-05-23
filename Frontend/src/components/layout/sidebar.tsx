"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Key, LayoutDashboard, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";
import { Button } from "@/components/ui/button";

const links = [
  { href: "/dashboard", label: "Dashboards", icon: LayoutDashboard },
  { href: "/api-keys", label: "API Keys", icon: Key },
  { href: "/ingest", label: "Ingest", icon: BarChart3 },
];

export function Sidebar() {
  const pathname = usePathname();
  const { organization, logout, user } = useAuthStore();

  return (
    <aside className="flex h-screen w-64 flex-col border-r border-border bg-card">
      <div className="border-b border-border p-6">
        <h1 className="text-lg font-bold text-primary">Analytics</h1>
        <p className="mt-1 truncate text-xs text-muted-foreground">{organization?.name}</p>
      </div>
      <nav className="flex-1 space-y-1 p-4">
        {links.map(({ href, label, icon: Icon }) => (
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
        ))}
      </nav>
      <div className="border-t border-border p-4">
        <p className="mb-2 truncate text-xs text-muted-foreground">{user?.email}</p>
        <Button variant="ghost" size="sm" className="w-full justify-start" onClick={() => logout()}>
          <LogOut className="mr-2 h-4 w-4" />
          Logout
        </Button>
      </div>
    </aside>
  );
}
