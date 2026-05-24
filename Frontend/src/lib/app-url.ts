/** Public frontend URL for invite/share links (must match deployed UI). */
export function getPublicAppUrl(): string | null {
  const configured = process.env.NEXT_PUBLIC_APP_URL?.replace(/\/$/, "");
  if (configured) return configured;
  if (typeof window !== "undefined") return window.location.origin;
  return null;
}

/** Prefer production URL when API still returns localhost links. */
export function resolveInviteLink(apiLink: string): string {
  try {
    const url = new URL(apiLink, typeof window !== "undefined" ? window.location.origin : undefined);
    const token = url.searchParams.get("token");
    const publicBase = process.env.NEXT_PUBLIC_APP_URL?.replace(/\/$/, "");
    if (publicBase && (url.hostname === "localhost" || url.hostname === "127.0.0.1") && token) {
      return `${publicBase}/accept-invite?token=${token}`;
    }
    if (apiLink.startsWith("http")) return apiLink;
    const origin = typeof window !== "undefined" ? window.location.origin : "";
    return `${origin}${apiLink.startsWith("/") ? apiLink : `/${apiLink}`}`;
  } catch {
    return apiLink;
  }
}
