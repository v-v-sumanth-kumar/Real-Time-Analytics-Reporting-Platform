"use client";

import { useAuthStore } from "@/stores/auth-store";
import { useEffect } from "react";

export function AuthHydrator() {
  const hydrate = useAuthStore((s) => s.hydrate);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  return null;
}
