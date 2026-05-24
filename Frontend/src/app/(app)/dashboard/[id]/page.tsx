"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { analyticsWs } from "@/lib/ws";
import { WidgetChart } from "@/components/charts/widget-chart";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RoleGate } from "@/components/layout/role-gate";

const TIME_RANGES = [
  { value: "1h", label: "Last hour" },
  { value: "24h", label: "Last 24 hours" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
];

const REFRESH_OPTIONS = [30, 60, 300];

type Widget = {
  id: string;
  type: string;
  title: string;
  query: Record<string, unknown>;
  refresh_interval_sec: number;
  position: Record<string, number>;
};

type Dashboard = {
  id: string;
  name: string;
  refresh_interval_sec: number;
  widgets: Widget[];
  is_public: boolean;
  share_url: string | null;
};

type Metrics = {
  widget_id: string;
  type: string;
  data: { label: string; value: number; timestamp?: string }[];
};

function WidgetCard({ widget, refreshInterval }: { widget: Widget; refreshInterval: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ["widget-metrics", widget.id],
    queryFn: () => apiFetch<Metrics>(`/api/v1/dashboards/widgets/${widget.id}/metrics`),
    refetchInterval: refreshInterval * 1000,
  });

  const metrics = data?.success ? data.data : null;

  return (
    <Card className="flex h-72 flex-col">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{widget.title}</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 min-h-0">
        {isLoading ? (
          <Skeleton className="h-full w-full" />
        ) : (
          <WidgetChart type={widget.type} title={widget.title} data={metrics?.data || []} />
        )}
      </CardContent>
    </Card>
  );
}

export default function DashboardDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [widgetForm, setWidgetForm] = useState({
    type: "line",
    title: "",
    event_name: "page_view",
    time_range: "24h",
  });

  const { data, isLoading } = useQuery({
    queryKey: ["dashboard", id],
    queryFn: () => apiFetch<Dashboard>(`/api/v1/dashboards/${id}`),
  });

  const dashboard = data?.success ? data.data : null;

  const addWidget = useMutation({
    mutationFn: () => {
      const y = (dashboard?.widgets.length || 0) * 3;
      return apiFetch(`/api/v1/dashboards/${id}/widgets`, {
        method: "POST",
        body: JSON.stringify({
          type: widgetForm.type,
          title: widgetForm.title,
          query: {
            event_name: widgetForm.event_name,
            metric: "count",
            time_range: widgetForm.time_range,
            granularity: widgetForm.time_range === "1h" ? "1h" : "1h",
          },
          position: { x: 0, y, w: 4, h: 3 },
        }),
      });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dashboard", id] }),
  });

  const shareMutation = useMutation({
    mutationFn: () =>
      apiFetch<Dashboard>(`/api/v1/dashboards/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_public: true }),
      }),
    onSuccess: (res) => {
      if (res.success && res.data.share_url) setShareUrl(res.data.share_url);
      queryClient.invalidateQueries({ queryKey: ["dashboard", id] });
    },
  });

  const unshareMutation = useMutation({
    mutationFn: () =>
      apiFetch(`/api/v1/dashboards/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_public: false }),
      }),
    onSuccess: () => {
      setShareUrl(null);
      queryClient.invalidateQueries({ queryKey: ["dashboard", id] });
    },
  });

  const refreshMutation = useMutation({
    mutationFn: (sec: number) =>
      apiFetch(`/api/v1/dashboards/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ refresh_interval_sec: sec }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dashboard", id] }),
  });

  useEffect(() => {
    analyticsWs.connect(id);
    const unsub = analyticsWs.subscribe((msg) => {
      if (msg.type === "event.ingested" || msg.type === "dashboard.refresh") {
        queryClient.invalidateQueries({ queryKey: ["widget-metrics"] });
      }
    });
    return () => {
      unsub();
      analyticsWs.disconnect();
    };
  }, [id, queryClient]);

  if (isLoading || !dashboard) {
    return (
      <div className="p-8">
        <Skeleton className="mb-4 h-10 w-64" />
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-72" />
          <Skeleton className="h-72" />
        </div>
      </div>
    );
  }

  const displayShareUrl = shareUrl || dashboard.share_url;

  return (
    <div className="p-8">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">{dashboard.name}</h1>
          <p className="text-sm text-muted-foreground">
            Auto-refresh every {dashboard.refresh_interval_sec}s
            {dashboard.is_public && " · Shared"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="h-10 rounded-md border border-input bg-background px-3 text-sm"
            value={dashboard.refresh_interval_sec}
            onChange={(e) => refreshMutation.mutate(Number(e.target.value))}
          >
            {REFRESH_OPTIONS.map((s) => (
              <option key={s} value={s}>
                Refresh {s}s
              </option>
            ))}
          </select>
          <RoleGate minRole="analyst">
            {dashboard.is_public ? (
              <Button variant="outline" onClick={() => unshareMutation.mutate()}>
                Disable sharing
              </Button>
            ) : (
              <Button variant="outline" onClick={() => shareMutation.mutate()}>
                Enable sharing
              </Button>
            )}
          </RoleGate>
        </div>
      </div>

      {displayShareUrl && (
        <Card className="mb-6">
          <CardContent className="py-4">
            <p className="text-sm text-muted-foreground">Public share link (read-only):</p>
            <code className="mt-1 block break-all text-sm">{displayShareUrl}</code>
          </CardContent>
        </Card>
      )}

      <RoleGate minRole="analyst">
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="text-base">Add widget</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-5">
            <div>
              <Label>Title</Label>
              <Input
                value={widgetForm.title}
                onChange={(e) => setWidgetForm({ ...widgetForm, title: e.target.value })}
              />
            </div>
            <div>
              <Label>Type</Label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={widgetForm.type}
                onChange={(e) => setWidgetForm({ ...widgetForm, type: e.target.value })}
              >
                <option value="line">Line</option>
                <option value="bar">Bar</option>
                <option value="pie">Pie</option>
                <option value="kpi">KPI</option>
              </select>
            </div>
            <div>
              <Label>Event name</Label>
              <Input
                value={widgetForm.event_name}
                onChange={(e) => setWidgetForm({ ...widgetForm, event_name: e.target.value })}
              />
            </div>
            <div>
              <Label>Time range</Label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={widgetForm.time_range}
                onChange={(e) => setWidgetForm({ ...widgetForm, time_range: e.target.value })}
              >
                {TIME_RANGES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <Button
                onClick={() => addWidget.mutate()}
                disabled={!widgetForm.title || addWidget.isPending}
              >
                Add widget
              </Button>
            </div>
          </CardContent>
        </Card>
      </RoleGate>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {dashboard.widgets.map((w) => (
          <WidgetCard
            key={w.id}
            widget={w}
            refreshInterval={w.refresh_interval_sec || dashboard.refresh_interval_sec}
          />
        ))}
      </div>
    </div>
  );
}
