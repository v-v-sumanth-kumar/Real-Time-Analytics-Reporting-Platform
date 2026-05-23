"use client";

import { useAuthStore } from "@/stores/auth-store";
import { apiFetch } from "@/lib/api";
import { useEffect } from "react";

export function AuthHydrator() {
  const hydrate = useAuthStore((s) => s.hydrate);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const setProfile = useAuthStore((s) => s.setProfile);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (!isAuthenticated) return;
    apiFetch<{ user: unknown; organization: unknown; role: string }>("/api/v1/auth/me").then(
      (res) => {
        if (res.success) {
          setProfile(res.data);
        }
      }
    );
  }, [isAuthenticated, setProfile]);

  return null;
}
