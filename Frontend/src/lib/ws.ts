import { getAccessToken, getOrganizationId } from "./api";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

type MessageHandler = (data: Record<string, unknown>) => void;

export class AnalyticsWebSocket {
  private ws: WebSocket | null = null;
  private handlers: Set<MessageHandler> = new Set();

  connect(dashboardId?: string) {
    const token = getAccessToken();
    const orgId = getOrganizationId();
    if (!token || !orgId) return;

    const params = new URLSearchParams({ token, org_id: orgId });
    if (dashboardId) params.set("dashboard_id", dashboardId);

    this.ws = new WebSocket(`${WS_URL}/ws?${params.toString()}`);

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handlers.forEach((h) => h(data));
      } catch {
        /* ignore */
      }
    };

    this.ws.onclose = () => {
      setTimeout(() => this.connect(dashboardId), 3000);
    };
  }

  subscribe(handler: MessageHandler) {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  disconnect() {
    this.ws?.close();
    this.ws = null;
  }

  ping() {
    this.ws?.send("ping");
  }
}

export const analyticsWs = new AnalyticsWebSocket();
