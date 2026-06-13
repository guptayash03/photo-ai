"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatBytes } from "@/lib/utils";
import type { DuplicatePair } from "@/types";

function DuplicateCard({ pair }: { pair: DuplicatePair }) {
  const queryClient = useQueryClient();

  const resolveMutation = useMutation({
    mutationFn: (action: "keep_a" | "keep_b" | "dismiss") =>
      api.duplicates.resolve(pair.id, action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["duplicates"] });
    },
  });

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <Badge variant={pair.duplicate_type === "exact" ? "default" : "secondary"}>
            {pair.duplicate_type}
          </Badge>
          <span className="text-sm text-muted-foreground">
            {Math.round(pair.similarity_score * 100)}% similar
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <div className="aspect-square overflow-hidden rounded-lg border bg-muted">
              {pair.image_a.thumbnail_url ? (
                <img
                  src={pair.image_a.thumbnail_url}
                  alt={pair.image_a.original_filename}
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex h-full items-center justify-center text-muted-foreground">A</div>
              )}
            </div>
            <div className="text-xs space-y-0.5">
              <p className="truncate font-medium">{pair.image_a.original_filename}</p>
              <p className="text-muted-foreground">{formatBytes(pair.image_a.file_size)}</p>
              {pair.image_a.width && (
                <p className="text-muted-foreground">{pair.image_a.width}x{pair.image_a.height}</p>
              )}
            </div>
            <Button
              size="sm"
              variant="outline"
              className="w-full"
              onClick={() => resolveMutation.mutate("keep_a")}
              disabled={resolveMutation.isPending}
            >
              Keep this
            </Button>
          </div>

          <div className="space-y-2">
            <div className="aspect-square overflow-hidden rounded-lg border bg-muted">
              {pair.image_b.thumbnail_url ? (
                <img
                  src={pair.image_b.thumbnail_url}
                  alt={pair.image_b.original_filename}
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex h-full items-center justify-center text-muted-foreground">B</div>
              )}
            </div>
            <div className="text-xs space-y-0.5">
              <p className="truncate font-medium">{pair.image_b.original_filename}</p>
              <p className="text-muted-foreground">{formatBytes(pair.image_b.file_size)}</p>
              {pair.image_b.width && (
                <p className="text-muted-foreground">{pair.image_b.width}x{pair.image_b.height}</p>
              )}
            </div>
            <Button
              size="sm"
              variant="outline"
              className="w-full"
              onClick={() => resolveMutation.mutate("keep_b")}
              disabled={resolveMutation.isPending}
            >
              Keep this
            </Button>
          </div>
        </div>

        <Button
          variant="ghost"
          size="sm"
          className="w-full mt-3"
          onClick={() => resolveMutation.mutate("dismiss")}
          disabled={resolveMutation.isPending}
        >
          Not duplicates — dismiss
        </Button>
      </CardContent>
    </Card>
  );
}

export default function DuplicatesPage() {
  const queryClient = useQueryClient();

  const { data: duplicates, isLoading } = useQuery({
    queryKey: ["duplicates"],
    queryFn: () => api.duplicates.list(),
  });

  const scanMutation = useMutation({
    mutationFn: () => api.duplicates.scan(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["duplicates"] });
    },
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-[400px] rounded-lg" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {duplicates?.length ?? 0} duplicate pairs to review
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => scanMutation.mutate()}
          disabled={scanMutation.isPending}
        >
          {scanMutation.isPending ? (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent mr-2" />
          ) : (
            <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          )}
          Scan for duplicates
        </Button>
      </div>

      {!duplicates || duplicates.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20">
          <svg className="h-16 w-16 text-muted-foreground/50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h2 className="mt-4 text-lg font-medium">No duplicates found</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Your library is clean! Run a scan to check for new duplicates.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {duplicates.map((pair) => (
            <DuplicateCard key={pair.id} pair={pair} />
          ))}
        </div>
      )}
    </div>
  );
}
