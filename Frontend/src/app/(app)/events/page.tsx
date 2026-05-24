"use client";

import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { analyticsWs } from "@/lib/ws";
import { useAuthStore } from "@/stores/auth-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

type StreamEvent = {
  id?: string;
  event_name: string;
  occurred_at: string;
  properties: Record<string, unknown>;
  user_id?: string | null;
  source?: string;
};

export default function EventsStreamPage() {
  const queryClient = useQueryClient();
  const orgId = useAuthStore((s) => s.organization?.id);

  const { data, isLoading } = useQuery({
    queryKey: ["events-stream", orgId],
    queryFn: () => apiFetch<StreamEvent[]>("/api/v1/events/stream?page=1&page_size=50"),
    enabled: !!orgId,
    refetchInterval: 5000,
    refetchOnWindowFocus: true,
  });

  useEffect(() => {
    if (!orgId) return;

    analyticsWs.connect();
    const unsub = analyticsWs.subscribe((msg) => {
      if (msg.type === "event.ingested") {
        queryClient.invalidateQueries({ queryKey: ["events-stream", orgId] });
      }
    });

    return () => {
      unsub();
      analyticsWs.disconnect();
    };
  }, [orgId, queryClient]);

  const events = data?.success ? data.data : [];

  return (
    <div className="p-8">
      <h1 className="mb-2 text-3xl font-bold">Live Event Stream</h1>
      <p className="mb-8 text-muted-foreground">Real-time tail of ingested events</p>

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <span className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
            Incoming events
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-64" />
          ) : events.length === 0 ? (
            <p className="text-sm text-muted-foreground">No events yet. Ingest events via API or CSV.</p>
          ) : (
            <div className="max-h-[600px] overflow-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="pb-2 pr-4">Time</th>
                    <th className="pb-2 pr-4">Event</th>
                    <th className="pb-2 pr-4">Source</th>
                    <th className="pb-2">Properties</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((e) => (
                    <tr key={e.id || `${e.event_name}-${e.occurred_at}`} className="border-b border-border/50">
                      <td className="py-2 pr-4 whitespace-nowrap">
                        {new Date(e.occurred_at).toLocaleString()}
                      </td>
                      <td className="py-2 pr-4 font-medium">{e.event_name}</td>
                      <td className="py-2 pr-4 capitalize">{e.source || "api"}</td>
                      <td className="py-2 truncate max-w-xs text-muted-foreground">
                        {JSON.stringify(e.properties)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
