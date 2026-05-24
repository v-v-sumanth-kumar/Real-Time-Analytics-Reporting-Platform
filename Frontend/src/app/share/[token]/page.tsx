"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { WidgetChart } from "@/components/charts/widget-chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Widget = {
  id: string;
  type: string;
  title: string;
};

type Dashboard = {
  id: string;
  name: string;
  widgets: Widget[];
  refresh_interval_sec: number;
};

type Metrics = {
  data: { label: string; value: number; timestamp?: string }[];
};

async function fetchPublic<T>(path: string): Promise<T | null> {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) return null;
  const json = await res.json();
  return json.success ? json.data : null;
}

function PublicWidget({ shareToken, widget }: { shareToken: string; widget: Widget }) {
  const { data, isLoading } = useQuery({
    queryKey: ["public-metrics", shareToken, widget.id],
    queryFn: () =>
      fetchPublic<Metrics>(`/api/v1/dashboards/public/${shareToken}/widgets/${widget.id}/metrics`),
    refetchInterval: 30000,
  });

  return (
    <Card className="flex h-72 flex-col">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{widget.title}</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 min-h-0">
        {isLoading ? (
          <Skeleton className="h-full w-full" />
        ) : (
          <WidgetChart type={widget.type} title={widget.title} data={data?.data || []} />
        )}
      </CardContent>
    </Card>
  );
}

export default function PublicDashboardPage() {
  const { token } = useParams<{ token: string }>();

  const { data: dashboard, isLoading } = useQuery({
    queryKey: ["public-dashboard", token],
    queryFn: () => fetchPublic<Dashboard>(`/api/v1/dashboards/public/${token}`),
  });

  if (isLoading || !dashboard) {
    return (
      <div className="min-h-screen bg-background p-8">
        <Skeleton className="mb-4 h-10 w-64" />
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-72" />
          <Skeleton className="h-72" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="mb-8">
        <p className="text-sm text-muted-foreground">Shared dashboard · read-only</p>
        <h1 className="text-3xl font-bold">{dashboard.name}</h1>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {dashboard.widgets.map((w) => (
          <PublicWidget key={w.id} shareToken={token} widget={w} />
        ))}
      </div>
    </div>
  );
}
