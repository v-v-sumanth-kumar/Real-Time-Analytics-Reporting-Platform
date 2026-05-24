import { create } from "zustand";
import { apiFetch, setAccessToken, setOrganizationId } from "@/lib/api";
import { Role } from "@/lib/permissions";

export type User = {
  id: string;
  email: string;
  full_name: string;
};

export type Organization = {
  id: string;
  name: string;
  slug: string;
};

export type ProfileUpdate = {
  user?: User;
  organization?: Organization | null;
  role?: string | null;
};

export type MeResponse = {
  user: User;
  organization: Organization | null;
  role: string | null;
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
  fetchProfile: () => Promise<void>;
  setProfile: (data: ProfileUpdate) => void;
};

function normalizeRole(value: string | null | undefined): Role | null {
  if (!value) return null;
  const role = value.toLowerCase();
  if (role === "viewer" || role === "analyst" || role === "admin" || role === "owner") {
    return role;
  }
  return null;
}

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
      const user = data.user ?? state.user;
      const organization =
        data.organization !== undefined ? data.organization : state.organization;
      const role =
        data.role !== undefined && data.role !== null
          ? normalizeRole(data.role)
          : state.role;
      if (user) persistSession(user, organization, role);
      if (organization?.id) setOrganizationId(organization.id);
      return { user, organization, role };
    });
  },

  fetchProfile: async () => {
    const res = await apiFetch<MeResponse>("/api/v1/auth/me");
    if (res.success) {
      useAuthStore.getState().setProfile(res.data);
    }
  },

  hydrate: () => {
    if (typeof window === "undefined") return;
    const token = sessionStorage.getItem("access_token");
    const user = sessionStorage.getItem("user");
    const org = sessionStorage.getItem("organization");
    const role = normalizeRole(sessionStorage.getItem("role"));
    if (token && user) {
      set({
        isAuthenticated: true,
        user: JSON.parse(user),
        organization: org ? JSON.parse(org) : null,
        role,
      });
      setAccessToken(token);
      if (org) setOrganizationId(JSON.parse(org).id);
      void useAuthStore.getState().fetchProfile();
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
      persistSession(res.data.user, res.data.organization, normalizeRole(res.data.role));
      set({
        user: res.data.user,
        organization: res.data.organization,
        role: normalizeRole(res.data.role),
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
      persistSession(res.data.user, res.data.organization, normalizeRole(res.data.role) || "owner");
      set({
        user: res.data.user,
        organization: res.data.organization,
        role: normalizeRole(res.data.role) || "owner",
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
