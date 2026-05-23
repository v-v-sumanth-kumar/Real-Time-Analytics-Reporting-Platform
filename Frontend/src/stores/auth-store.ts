import { create } from "zustand";
import { apiFetch, setAccessToken, setOrganizationId } from "@/lib/api";
import { Role } from "@/lib/permissions";

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
  role: Role | null;
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
  setProfile: (data: {
    user?: User;
    organization?: Organization | null;
    role?: string | null;
  }) => void;
};

function persistSession(user: User, organization: Organization | null, role: Role | null) {
  sessionStorage.setItem("user", JSON.stringify(user));
  if (organization) sessionStorage.setItem("organization", JSON.stringify(organization));
  if (role) sessionStorage.setItem("role", role);
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  organization: null,
  role: null,
  isLoading: false,
  isAuthenticated: false,

  setProfile: (data) => {
    set((state) => {
      const user = (data.user as User) || state.user;
      const organization =
        data.organization !== undefined ? (data.organization as Organization | null) : state.organization;
      const role = (data.role as Role) || state.role;
      if (user) persistSession(user, organization, role);
      if (organization?.id) setOrganizationId(organization.id);
      return { user, organization, role };
    });
  },

  hydrate: () => {
    if (typeof window === "undefined") return;
    const token = sessionStorage.getItem("access_token");
    const user = sessionStorage.getItem("user");
    const org = sessionStorage.getItem("organization");
    const role = sessionStorage.getItem("role") as Role | null;
    if (token && user) {
      set({
        isAuthenticated: true,
        user: JSON.parse(user),
        organization: org ? JSON.parse(org) : null,
        role,
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
        role: Role;
      }>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      if (!res.success) throw new Error(res.error?.message || "Login failed");
      setAccessToken(res.data.access_token);
      setOrganizationId(res.data.organization?.id || null);
      persistSession(res.data.user, res.data.organization, res.data.role);
      set({
        user: res.data.user,
        organization: res.data.organization,
        role: res.data.role,
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
        role: Role;
      }>("/api/v1/auth/signup", {
        method: "POST",
        body: JSON.stringify(data),
      });
      if (!res.success) throw new Error(res.error?.message || "Signup failed");
      setAccessToken(res.data.access_token);
      setOrganizationId(res.data.organization.id);
      persistSession(res.data.user, res.data.organization, res.data.role || "owner");
      set({
        user: res.data.user,
        organization: res.data.organization,
        role: res.data.role || "owner",
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
    set({ user: null, organization: null, role: null, isAuthenticated: false });
  },
}));
