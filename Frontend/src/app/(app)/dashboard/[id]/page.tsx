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

type Widget = {
  id: string;
  type: string;
  title: string;
  query: Record<string, unknown>;
  refresh_interval_sec: number;
};

type Dashboard = {
  id: string;
  name: string;
  refresh_interval_sec: number;
  widgets: Widget[];
  is_public: boolean;
};

type Metrics = {
  widget_id: string;
  type: string;
  data: { label: string; value: number; timestamp?: string }[];
};

function WidgetCard({ widget, refreshInterval }: { widget: Widget; refreshInterval: number }) {
  const { data, isLoading, refetch } = useQuery({
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
          <WidgetChart
            type={widget.type}
            title={widget.title}
            data={metrics?.data || []}
          />
        )}
      </CardContent>
    </Card>
  );
}

export default function DashboardDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
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
    mutationFn: () =>
      apiFetch(`/api/v1/dashboards/${id}/widgets`, {
        method: "POST",
        body: JSON.stringify({
          type: widgetForm.type,
          title: widgetForm.title,
          query: {
            event_name: widgetForm.event_name,
            metric: "count",
            time_range: widgetForm.time_range,
            granularity: "1h",
          },
          position: { x: 0, y: 0, w: 4, h: 3 },
        }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dashboard", id] }),
  });

  const shareMutation = useMutation({
    mutationFn: () =>
      apiFetch(`/api/v1/dashboards/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_public: true }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dashboard", id] }),
  });

  useEffect(() => {
    analyticsWs.connect(id);
    const unsub = analyticsWs.subscribe((msg) => {
      if (msg.type === "event.ingested") {
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

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{dashboard.name}</h1>
          <p className="text-sm text-muted-foreground">
            Auto-refresh every {dashboard.refresh_interval_sec}s
            {dashboard.is_public && " · Shared"}
          </p>
        </div>
        <Button variant="outline" onClick={() => shareMutation.mutate()}>
          Enable sharing
        </Button>
      </div>

      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="text-base">Add widget</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-4">
          <div>
            <Label>Title</Label>
            <Input value={widgetForm.title} onChange={(e) => setWidgetForm({ ...widgetForm, title: e.target.value })} />
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
