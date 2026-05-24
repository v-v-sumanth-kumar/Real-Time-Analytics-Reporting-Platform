"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { resolveInviteLink } from "@/lib/app-url";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";

type Member = {
  id: string;
  user_id: string;
  email: string;
  full_name: string;
  role: string;
};

export default function TeamPage() {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("viewer");
  const [inviteLink, setInviteLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function copyInviteLink() {
    if (!inviteLink) return;
    await navigator.clipboard.writeText(inviteLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const { data, isLoading } = useQuery({
    queryKey: ["members"],
    queryFn: () => apiFetch<Member[]>("/api/v1/organizations/members"),
  });

  const inviteMutation = useMutation({
    mutationFn: () =>
      apiFetch<{ invite_link: string; email: string; role: string }>(
        "/api/v1/organizations/invitations",
        { method: "POST", body: JSON.stringify({ email, role }) }
      ),
    onSuccess: (res) => {
      if (res.success) {
        setInviteLink(resolveInviteLink(res.data.invite_link));
        setEmail("");
      }
    },
  });

  const members = data?.success ? data.data : [];

  return (
    <div className="p-8">
      <h1 className="mb-2 text-3xl font-bold">Team</h1>
      <p className="mb-8 text-muted-foreground">Manage members and send invitations</p>

      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="text-base">Invite member</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div>
            <Label>Email</Label>
            <Input value={email} onChange={(e) => setEmail(e.target.value)} type="email" />
          </div>
          <div>
            <Label>Role</Label>
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              <option value="viewer">Viewer</option>
              <option value="analyst">Analyst</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div className="flex items-end">
            <Button onClick={() => inviteMutation.mutate()} disabled={!email || inviteMutation.isPending}>
              Send invite
            </Button>
          </div>
        </CardContent>
        {inviteLink && (
          <CardContent className="border-t border-border pt-4">
            <p className="text-sm text-muted-foreground">
              Share this link with the invitee (must be a URL they can open in a browser):
            </p>
            <code className="mt-2 block break-all rounded bg-muted p-3 text-sm">{inviteLink}</code>
            <Button variant="outline" size="sm" className="mt-3" onClick={() => copyInviteLink()}>
              {copied ? "Copied!" : "Copy link"}
            </Button>
            {inviteLink.includes("localhost") && (
              <p className="mt-3 text-xs text-amber-400">
                This link only works on your machine. Deploy the frontend and set FRONTEND_URL on the
                backend (and NEXT_PUBLIC_APP_URL on the frontend) to your public URL.
              </p>
            )}
          </CardContent>
        )}
      </Card>

      {isLoading ? (
        <Skeleton className="h-32" />
      ) : (
        <div className="space-y-3">
          {members.map((m) => (
            <Card key={m.id}>
              <CardContent className="flex items-center justify-between py-4">
                <div>
                  <p className="font-medium">{m.full_name || m.email}</p>
                  <p className="text-sm text-muted-foreground">{m.email}</p>
                </div>
                <span className="rounded-full bg-primary/10 px-3 py-1 text-xs capitalize text-primary">
                  {m.role}
                </span>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
