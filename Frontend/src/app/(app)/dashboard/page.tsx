"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Plus } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { useState } from "react";

type Dashboard = {
  id: string;
  name: string;
  description: string | null;
  widgets: unknown[];
};

export default function DashboardListPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["dashboards"],
    queryFn: () => apiFetch<Dashboard[]>("/api/v1/dashboards"),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      apiFetch<Dashboard>("/api/v1/dashboards", {
        method: "POST",
        body: JSON.stringify({ name, description: null }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboards"] });
      setName("");
      setShowCreate(false);
    },
  });

  const dashboards = data?.success ? data.data : [];

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboards</h1>
          <p className="text-muted-foreground">Build and monitor your analytics</p>
        </div>
        <Button onClick={() => setShowCreate(!showCreate)}>
          <Plus className="mr-2 h-4 w-4" />
          New dashboard
        </Button>
      </div>

      {showCreate && (
        <Card className="mb-6">
          <CardContent className="flex gap-4 pt-6">
            <Input placeholder="Dashboard name" value={name} onChange={(e) => setName(e.target.value)} />
            <Button onClick={() => createMutation.mutate()} disabled={!name || createMutation.isPending}>
              Create
            </Button>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {dashboards.map((d) => (
            <Link key={d.id} href={`/dashboard/${d.id}`}>
              <Card className="transition-colors hover:border-primary/50">
                <CardHeader>
                  <CardTitle className="text-lg">{d.name}</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    {Array.isArray(d.widgets) ? d.widgets.length : 0} widgets
                  </p>
                </CardHeader>
              </Card>
            </Link>
          ))}
          {dashboards.length === 0 && (
            <p className="col-span-full text-muted-foreground">No dashboards yet. Create one to get started.</p>
          )}
        </div>
      )}
    </div>
  );
}
