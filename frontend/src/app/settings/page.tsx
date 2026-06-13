"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatBytes, formatDate } from "@/lib/utils";

export default function SettingsPage() {
  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: () => api.stats.overview(),
  });

  const { data: gpStatus } = useQuery({
    queryKey: ["google-photos-status"],
    queryFn: () => api.googlePhotos.status(),
  });

  const syncMutation = useMutation({
    mutationFn: () => api.googlePhotos.sync(),
  });

  const scanMutation = useMutation({
    mutationFn: () => api.duplicates.scan(),
  });

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Google Photos</CardTitle>
          <CardDescription>Manage your Google Photos connection</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm">Status:</span>
              {gpStatus?.connected ? (
                <Badge variant="default">Connected</Badge>
              ) : (
                <Badge variant="secondary">Not connected</Badge>
              )}
            </div>
            {gpStatus?.last_sync && (
              <span className="text-xs text-muted-foreground">
                Last sync: {formatDate(gpStatus.last_sync)}
              </span>
            )}
          </div>
          <div className="flex gap-2">
            {gpStatus?.connected ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => syncMutation.mutate()}
                disabled={syncMutation.isPending}
              >
                {syncMutation.isPending ? "Syncing..." : "Sync Now"}
              </Button>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={async () => {
                  const { url } = await api.googlePhotos.getAuthUrl();
                  window.location.href = url;
                }}
              >
                Connect Google Photos
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Storage</CardTitle>
          <CardDescription>Your photo library storage usage</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Total storage used</span>
              <span className="font-medium">
                {stats ? formatBytes(stats.storage_used_bytes) : "—"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Total photos</span>
              <span className="font-medium">{stats?.total_images.toLocaleString() ?? "—"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">People identified</span>
              <span className="font-medium">{stats?.total_people ?? "—"}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Processing</CardTitle>
          <CardDescription>Trigger reprocessing tasks</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Duplicate Scan</p>
              <p className="text-xs text-muted-foreground">
                Scan all photos for exact and near duplicates
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => scanMutation.mutate()}
              disabled={scanMutation.isPending}
            >
              {scanMutation.isPending ? "Scanning..." : "Run Scan"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>About</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-1">
          <p><strong>PhotoAI</strong> — Intelligent Photo Management Platform</p>
          <p>Built with Next.js, FastAPI, Vertex AI, and pgvector</p>
          <p>AI-powered categorization, face recognition, and natural language search</p>
        </CardContent>
      </Card>
    </div>
  );
}
