"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { analyticsWs } from "@/lib/ws";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { RoleGate } from "@/components/layout/role-gate";

type AlertRule = {
  id: string;
  name: string;
  event_name: string | null;
  threshold: number;
  operator: string;
  window_minutes: number;
  status: string;
  last_value: number | null;
};

type Incident = {
  id: string;
  triggered_value: number;
  triggered_at: string;
  status: string;
  resolved_at: string | null;
};

export default function AlertsPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    event_name: "",
    threshold: 100,
    window_minutes: 10,
    webhook_url: "",
  });
  const [toast, setToast] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["alerts"],
    queryFn: () => apiFetch<AlertRule[]>("/api/v1/alerts"),
  });

  const { data: historyData } = useQuery({
    queryKey: ["alert-history", selectedId],
    queryFn: () => apiFetch<Incident[]>(`/api/v1/alerts/${selectedId}/history`),
    enabled: !!selectedId,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      apiFetch("/api/v1/alerts", {
        method: "POST",
        body: JSON.stringify({
          name: form.name,
          event_name: form.event_name || null,
          threshold: form.threshold,
          window_minutes: form.window_minutes,
          operator: "gt",
          notification_channels: {
            in_app: true,
            email: false,
            webhook_url: form.webhook_url || null,
          },
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      setForm({ name: "", event_name: "", threshold: 100, window_minutes: 10, webhook_url: "" });
    },
  });

  const muteMutation = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/api/v1/alerts/${id}/mute`, {
        method: "POST",
        body: JSON.stringify({ minutes: 60 }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] }),
  });

  const unmuteMutation = useMutation({
    mutationFn: (id: string) => apiFetch(`/api/v1/alerts/${id}/unmute`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] }),
  });

  useEffect(() => {
    analyticsWs.connect();
    const unsub = analyticsWs.subscribe((msg) => {
      if (msg.type === "alert.triggered" || msg.type === "alert.resolved") {
        const payload = msg.payload as { message?: string } | undefined;
        setToast(payload?.message || String(msg.type));
        queryClient.invalidateQueries({ queryKey: ["alerts"] });
      }
    });
    return () => {
      unsub();
      analyticsWs.disconnect();
    };
  }, [queryClient]);

  const alerts = data?.success ? data.data : [];
  const history = historyData?.success ? historyData.data : [];

  return (
    <div className="p-8">
      <h1 className="mb-2 text-3xl font-bold">Alerts</h1>
      <p className="mb-8 text-muted-foreground">Threshold-based alerts with in-app and webhook notifications</p>

      {toast && (
        <div className="mb-4 rounded-md border border-amber-500/50 bg-amber-500/10 px-4 py-3 text-sm">
          {toast}
          <button className="ml-4 underline" onClick={() => setToast(null)}>
            dismiss
          </button>
        </div>
      )}

      <RoleGate minRole="analyst">
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="text-base">Create alert rule</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-3">
            <div>
              <Label>Name</Label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div>
              <Label>Event name (optional)</Label>
              <Input
                value={form.event_name}
                onChange={(e) => setForm({ ...form, event_name: e.target.value })}
                placeholder="page_view"
              />
            </div>
            <div>
              <Label>Threshold (count)</Label>
              <Input
                type="number"
                value={form.threshold}
                onChange={(e) => setForm({ ...form, threshold: Number(e.target.value) })}
              />
            </div>
            <div>
              <Label>Window (minutes)</Label>
              <Input
                type="number"
                value={form.window_minutes}
                onChange={(e) => setForm({ ...form, window_minutes: Number(e.target.value) })}
              />
            </div>
            <div>
              <Label>Webhook URL (Slack-compatible)</Label>
              <Input
                value={form.webhook_url}
                onChange={(e) => setForm({ ...form, webhook_url: e.target.value })}
                placeholder="https://hooks.slack.com/..."
              />
            </div>
            <div className="flex items-end">
              <Button onClick={() => createMutation.mutate()} disabled={!form.name}>
                Create alert
              </Button>
            </div>
          </CardContent>
        </Card>
      </RoleGate>

      {isLoading ? (
        <Skeleton className="h-32" />
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-3">
            {alerts.map((a) => (
              <Card
                key={a.id}
                className={selectedId === a.id ? "ring-2 ring-primary" : ""}
                onClick={() => setSelectedId(a.id)}
              >
                <CardContent className="py-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium">{a.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {a.event_name || "all events"} · {a.operator} {a.threshold} / {a.window_minutes}m
                      </p>
                      {a.last_value != null && (
                        <p className="text-xs text-muted-foreground">Last value: {a.last_value}</p>
                      )}
                    </div>
                    <span
                      className={`rounded-full px-2 py-1 text-xs capitalize ${
                        a.status === "triggered"
                          ? "bg-red-500/20 text-red-400"
                          : a.status === "muted"
                            ? "bg-gray-500/20 text-gray-400"
                            : "bg-green-500/20 text-green-400"
                      }`}
                    >
                      {a.status}
                    </span>
                  </div>
                  <RoleGate minRole="analyst">
                    <div className="mt-3 flex gap-2">
                      {a.status === "muted" ? (
                        <Button size="sm" variant="outline" onClick={() => unmuteMutation.mutate(a.id)}>
                          Unmute
                        </Button>
                      ) : (
                        <Button size="sm" variant="outline" onClick={() => muteMutation.mutate(a.id)}>
                          Mute 1h
                        </Button>
                      )}
                    </div>
                  </RoleGate>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Alert history</CardTitle>
            </CardHeader>
            <CardContent>
              {!selectedId ? (
                <p className="text-sm text-muted-foreground">Select an alert to view history</p>
              ) : history.length === 0 ? (
                <p className="text-sm text-muted-foreground">No incidents yet</p>
              ) : (
                <div className="space-y-2">
                  {history.map((h) => (
                    <div key={h.id} className="rounded border border-border p-3 text-sm">
                      <p className="font-medium capitalize">{h.status}</p>
                      <p className="text-muted-foreground">
                        Value: {h.triggered_value} · {new Date(h.triggered_at).toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
