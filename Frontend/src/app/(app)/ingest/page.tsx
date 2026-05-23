"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function IngestPage() {
  const [apiKey, setApiKey] = useState("");
  const [result, setResult] = useState("");

  async function sendTestEvent() {
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
    setResult(JSON.stringify(json, null, 2));
  }

  return (
    <div className="p-8">
      <h1 className="mb-2 text-3xl font-bold">Event Ingestion</h1>
      <p className="mb-8 text-muted-foreground">
        Send events via API key. CSV upload available from the API for authenticated users.
      </p>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Test ingest</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <input
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
            placeholder="X-API-Key"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
          <button
            onClick={sendTestEvent}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
          >
            Send test event
          </button>
          {result && (
            <pre className="overflow-auto rounded bg-muted p-4 text-xs">{result}</pre>
          )}
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">API reference</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 font-mono text-sm text-muted-foreground">
          <p>POST {API_URL}/api/v1/events</p>
          <p>POST {API_URL}/api/v1/events/batch</p>
          <p>POST {API_URL}/api/v1/events/upload (multipart, JWT)</p>
        </CardContent>
      </Card>
    </div>
  );
}
