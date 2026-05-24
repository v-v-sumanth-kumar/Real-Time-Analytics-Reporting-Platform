"use client";

import { useRef, useState } from "react";
import { apiUploadFile } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type IngestResult = {
  accepted: number;
  ingest_id: string | null;
};

export default function IngestPage() {
  const [apiKey, setApiKey] = useState("");
  const [apiKeyResult, setApiKeyResult] = useState("");
  const [apiKeyError, setApiKeyError] = useState("");
  const [apiKeyLoading, setApiKeyLoading] = useState(false);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvResult, setCsvResult] = useState("");
  const [csvError, setCsvError] = useState("");
  const [csvLoading, setCsvLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function sendTestEvent() {
    setApiKeyLoading(true);
    setApiKeyResult("");
    setApiKeyError("");
    try {
      const res = await fetch(`${API_URL}/api/v1/events`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": apiKey,
        },
        body: JSON.stringify({
          event_name: "page_view",
          properties: { page: "/home", source: "test" },
        }),
      });
      const json = await res.json();
      if (!res.ok || !json.success) {
        setApiKeyError(json.error?.message || `Request failed (${res.status})`);
        return;
      }
      setApiKeyResult(JSON.stringify(json, null, 2));
    } catch (e) {
      setApiKeyError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setApiKeyLoading(false);
    }
  }

  async function uploadCsv() {
    if (!csvFile) return;
    setCsvLoading(true);
    setCsvError("");
    setCsvResult("");
    try {
      const res = await apiUploadFile<IngestResult>("/api/v1/events/upload", csvFile);
      if (!res.success) {
        setCsvError(res.error?.message || "Upload failed");
        return;
      }
      setCsvResult(JSON.stringify(res, null, 2));
      setCsvFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (e) {
      setCsvError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setCsvLoading(false);
    }
  }

  return (
    <div className="p-8">
      <h1 className="mb-2 text-3xl font-bold">Event Ingestion</h1>
      <p className="mb-8 text-muted-foreground">
        Send events with an API key or upload a CSV while signed in (Analyst role or higher).
      </p>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Test ingest (API key)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Sends a fixed test payload ({`{"event_name":"page_view", ...}`}). The API returns{" "}
              <strong>202 Accepted</strong> after queuing — it does not write to the database
              immediately. A Celery worker must drain the queue (usually within ~5 seconds).
              Events are stored under the <strong>API key&apos;s organization</strong>; check Live
              Events while logged into that same org.
            </p>
            <div className="space-y-2">
              <Label htmlFor="api-key">X-API-Key</Label>
              <Input
                id="api-key"
                placeholder="ak_..."
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
            </div>
            <Button onClick={sendTestEvent} disabled={!apiKey || apiKeyLoading}>
              {apiKeyLoading ? "Sending..." : "Send test event"}
            </Button>
            {apiKeyError && <p className="text-sm text-red-500">{apiKeyError}</p>}
            {apiKeyResult && (
              <pre className="overflow-auto rounded bg-muted p-4 text-xs">{apiKeyResult}</pre>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Upload CSV</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Uses your session (JWT). Required columns:{" "}
              <code className="text-xs">event_name</code> or{" "}
              <code className="text-xs">event</code>. Optional:{" "}
              <code className="text-xs">occurred_at</code>,{" "}
              <code className="text-xs">user_id</code>,{" "}
              <code className="text-xs">session_id</code>, plus any property columns.
            </p>
            <div className="space-y-2">
              <Label htmlFor="csv-file">CSV file</Label>
              <Input
                id="csv-file"
                ref={fileInputRef}
                type="file"
                accept=".csv,text/csv"
                onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)}
              />
            </div>
            <Button onClick={uploadCsv} disabled={!csvFile || csvLoading}>
              {csvLoading ? "Uploading..." : "Upload CSV"}
            </Button>
            {csvError && <p className="text-sm text-red-500">{csvError}</p>}
            {csvResult && (
              <pre className="overflow-auto rounded bg-muted p-4 text-xs">{csvResult}</pre>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">API reference</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 font-mono text-sm text-muted-foreground">
          <p>POST {API_URL}/api/v1/events</p>
          <p>POST {API_URL}/api/v1/events/batch</p>
          <p>POST {API_URL}/api/v1/events/upload</p>
        </CardContent>
      </Card>
    </div>
  );
}
