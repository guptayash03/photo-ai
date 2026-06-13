"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { useState } from "react";
import type { FaceCluster } from "@/types";

function ClusterCard({ cluster }: { cluster: FaceCluster }) {
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState(cluster.name || "");

  const renameMutation = useMutation({
    mutationFn: (newName: string) => api.faces.renameCluster(cluster.id, newName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["face-clusters"] });
      setIsEditing(false);
    },
  });

  return (
    <div className="group relative rounded-lg border bg-card p-4 transition-shadow hover:shadow-md">
      <Link href={`/faces/${cluster.id}`} className="block">
        <div className="flex flex-col items-center text-center">
          <div className="h-20 w-20 overflow-hidden rounded-full border-2 border-primary/20 bg-muted">
            {cluster.representative_face_url ? (
              <img
                src={cluster.representative_face_url}
                alt={cluster.name || "Unknown person"}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full items-center justify-center">
                <svg className="h-8 w-8 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
            )}
          </div>
          <Badge variant="secondary" className="mt-3">
            {cluster.face_count} {cluster.face_count === 1 ? "photo" : "photos"}
          </Badge>
        </div>
      </Link>

      <div className="mt-2 text-center">
        {isEditing ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              renameMutation.mutate(name);
            }}
            className="flex gap-1"
          >
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded border bg-background px-2 py-1 text-center text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder="Enter name"
              autoFocus
              onBlur={() => setIsEditing(false)}
            />
          </form>
        ) : (
          <button
            onClick={() => setIsEditing(true)}
            className="text-sm font-medium hover:text-primary transition-colors"
          >
            {cluster.name || "Unknown person"}
          </button>
        )}
      </div>
    </div>
  );
}

export default function FacesPage() {
  const { data: clusters, isLoading } = useQuery({
    queryKey: ["face-clusters"],
    queryFn: () => api.faces.listClusters(),
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
        {Array.from({ length: 12 }).map((_, i) => (
          <div key={i} className="flex flex-col items-center gap-2 p-4">
            <Skeleton className="h-20 w-20 rounded-full" />
            <Skeleton className="h-4 w-16" />
          </div>
        ))}
      </div>
    );
  }

  if (!clusters || clusters.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <svg className="h-16 w-16 text-muted-foreground/50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <h2 className="mt-4 text-lg font-medium">No people found yet</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload photos with faces to start grouping people
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {clusters.length} {clusters.length === 1 ? "person" : "people"} found
        </p>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
        {clusters.map((cluster) => (
          <ClusterCard key={cluster.id} cluster={cluster} />
        ))}
      </div>
    </div>
  );
}
