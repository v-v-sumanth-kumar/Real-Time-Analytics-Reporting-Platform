import { getAccessToken, getOrganizationId } from "./api";

function resolveWsUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_WS_URL?.trim();
  if (explicit) return explicit;
  const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  return api.replace(/^https:/, "wss:").replace(/^http:/, "ws:");
}

type MessageHandler = (data: Record<string, unknown>) => void;

export class AnalyticsWebSocket {
  private ws: WebSocket | null = null;
  private handlers: Set<MessageHandler> = new Set();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private dashboardId: string | undefined;

  connect(dashboardId?: string) {
    this.dashboardId = dashboardId;
    const token = getAccessToken();
    const orgId = getOrganizationId();
    if (!token || !orgId) {
      this.scheduleReconnect();
      return;
    }

    if (this.ws?.readyState === WebSocket.OPEN) return;

    const params = new URLSearchParams({ token, org_id: orgId });
    if (dashboardId) params.set("dashboard_id", dashboardId);

    this.ws = new WebSocket(`${resolveWsUrl()}/ws?${params.toString()}`);

    this.ws.onopen = () => {
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handlers.forEach((h) => h(data));
      } catch {
        /* ignore */
      }
    };

    this.ws.onclose = () => {
      this.ws = null;
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect(this.dashboardId);
    }, 3000);
  }

  subscribe(handler: MessageHandler) {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  ping() {
    this.ws?.send("ping");
  }
}

export const analyticsWs = new AnalyticsWebSocket();
