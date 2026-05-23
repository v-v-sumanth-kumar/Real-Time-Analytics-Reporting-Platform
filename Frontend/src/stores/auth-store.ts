import { create } from "zustand";
import { apiFetch, setAccessToken, setOrganizationId } from "@/lib/api";

type User = {
  id: string;
  email: string;
  full_name: string;
};

type Organization = {
  id: string;
  name: string;
  slug: string;
};

type AuthState = {
  user: User | null;
  organization: Organization | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (data: {
    email: string;
    password: string;
    full_name: string;
    organization_name: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
  hydrate: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  organization: null,
  isLoading: false,
  isAuthenticated: false,

  hydrate: () => {
    if (typeof window === "undefined") return;
    const token = sessionStorage.getItem("access_token");
    const user = sessionStorage.getItem("user");
    const org = sessionStorage.getItem("organization");
    if (token && user) {
      set({
        isAuthenticated: true,
        user: JSON.parse(user),
        organization: org ? JSON.parse(org) : null,
      });
      setAccessToken(token);
      if (org) setOrganizationId(JSON.parse(org).id);
    }
  },

  login: async (email, password) => {
    set({ isLoading: true });
    try {
      const res = await apiFetch<{
        access_token: string;
        user: User;
        organization: Organization;
      }>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      if (!res.success) throw new Error(res.error?.message || "Login failed");
      setAccessToken(res.data.access_token);
      setOrganizationId(res.data.organization?.id || null);
      sessionStorage.setItem("user", JSON.stringify(res.data.user));
      if (res.data.organization) {
        sessionStorage.setItem("organization", JSON.stringify(res.data.organization));
      }
      set({
        user: res.data.user,
        organization: res.data.organization,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (e) {
      set({ isLoading: false });
      throw e;
    }
  },

  signup: async (data) => {
    set({ isLoading: true });
    try {
      const res = await apiFetch<{
        access_token: string;
        user: User;
        organization: Organization;
      }>("/api/v1/auth/signup", {
        method: "POST",
        body: JSON.stringify(data),
      });
      if (!res.success) throw new Error(res.error?.message || "Signup failed");
      setAccessToken(res.data.access_token);
      setOrganizationId(res.data.organization.id);
      sessionStorage.setItem("user", JSON.stringify(res.data.user));
      sessionStorage.setItem("organization", JSON.stringify(res.data.organization));
      set({
        user: res.data.user,
        organization: res.data.organization,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (e) {
      set({ isLoading: false });
      throw e;
    }
  },

  logout: async () => {
    await apiFetch("/api/v1/auth/logout", { method: "POST" });
    setAccessToken(null);
    setOrganizationId(null);
    sessionStorage.clear();
    set({ user: null, organization: null, isAuthenticated: false });
  },
}));
