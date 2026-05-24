"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";

type ApiKey = {
  id: string;
  name: string;
  key_prefix: string;
  rate_limit_rpm: number;
  created_at: string;
};

export default function ApiKeysPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [rateLimit, setRateLimit] = useState(10000);
  const [newKey, setNewKey] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["api-keys"],
    queryFn: () => apiFetch<ApiKey[]>("/api/v1/api-keys"),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      apiFetch<ApiKey & { key: string }>("/api/v1/api-keys", {
        method: "POST",
        body: JSON.stringify({ name, rate_limit_rpm: rateLimit }),
      }),
    onSuccess: (res) => {
      if (res.success && "key" in res.data) {
        setNewKey((res.data as ApiKey & { key: string }).key);
      }
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
      setName("");
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/api/v1/api-keys/${id}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["api-keys"] }),
  });

  const rotateMutation = useMutation({
    mutationFn: (id: string) =>
      apiFetch<ApiKey & { key: string }>(`/api/v1/api-keys/${id}/rotate`, { method: "POST" }),
    onSuccess: (res) => {
      if (res.success && "key" in res.data) {
        setNewKey((res.data as ApiKey & { key: string }).key);
      }
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });

  const keys = data?.success ? data.data : [];

  return (
    <div className="p-8">
      <h1 className="mb-2 text-3xl font-bold">API Keys</h1>
      <p className="mb-8 text-muted-foreground">Use keys to ingest events from your applications</p>

      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="text-base">Create API key</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Production ingest" />
          </div>
          <div className="w-40">
            <Label>Rate limit (req/min)</Label>
            <Input
              type="number"
              value={rateLimit}
              onChange={(e) => setRateLimit(Number(e.target.value))}
            />
          </div>
          <Button className="self-end" onClick={() => createMutation.mutate()} disabled={!name}>
            Create
          </Button>
        </CardContent>
        {newKey && (
          <CardContent className="border-t border-border pt-4">
            <p className="text-sm text-amber-400">Copy this key now — it won&apos;t be shown again:</p>
            <code className="mt-2 block break-all rounded bg-muted p-3 text-sm">{newKey}</code>
          </CardContent>
        )}
      </Card>

      {isLoading ? (
        <Skeleton className="h-32" />
      ) : (
        <div className="space-y-4">
          {keys.map((k) => (
            <Card key={k.id}>
              <CardContent className="flex flex-wrap items-center justify-between gap-4 py-4">
                <div>
                  <p className="font-medium">{k.name}</p>
                  <p className="text-sm text-muted-foreground">
                    ak_{k.key_prefix}... · {k.rate_limit_rpm} req/min
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => rotateMutation.mutate(k.id)}>
                    Rotate
                  </Button>
                  <Button size="sm" variant="destructive" onClick={() => revokeMutation.mutate(k.id)}>
                    Revoke
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
