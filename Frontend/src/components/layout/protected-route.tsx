"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";
import { Skeleton } from "@/components/ui/skeleton";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, hydrate } = useAuthStore();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    const token = typeof window !== "undefined" ? sessionStorage.getItem("access_token") : null;
    if (!token && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, router]);

  if (typeof window !== "undefined" && !sessionStorage.getItem("access_token") && !isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Skeleton className="h-8 w-48" />
      </div>
    );
  }

  return <>{children}</>;
}
