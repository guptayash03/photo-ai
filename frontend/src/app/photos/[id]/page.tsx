"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatBytes, formatDate } from "@/lib/utils";
import { useParams, useRouter } from "next/navigation";
import { Skeleton } from "@/components/ui/skeleton";

export default function PhotoDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const id = params.id as string;

  const { data: image, isLoading } = useQuery({
    queryKey: ["image", id],
    queryFn: () => api.images.get(id),
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.images.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["photos"] });
      router.push("/photos");
    },
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Skeleton className="col-span-2 aspect-video rounded-lg" />
        <div className="space-y-4">
          <Skeleton className="h-[200px]" />
          <Skeleton className="h-[150px]" />
        </div>
      </div>
    );
  }

  if (!image) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => router.back()}>
          <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back
        </Button>
        <Button
          variant="destructive"
          size="sm"
          onClick={() => {
            if (confirm("Delete this photo?")) deleteMutation.mutate();
          }}
        >
          Delete
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="col-span-2">
          <div className="overflow-hidden rounded-lg border bg-muted">
            <img
              src={image.storage_url || image.thumbnail_url || ""}
              alt={image.original_filename}
              className="w-full h-auto max-h-[70vh] object-contain"
            />
          </div>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Filename</span>
                <span className="font-medium truncate ml-2 max-w-[180px]">{image.original_filename}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Size</span>
                <span>{formatBytes(image.file_size)}</span>
              </div>
              {image.width && image.height && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Dimensions</span>
                  <span>{image.width} x {image.height}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-muted-foreground">Type</span>
                <span>{image.mime_type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Source</span>
                <Badge variant="outline" className="capitalize">{image.source}</Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Uploaded</span>
                <span>{formatDate(image.created_at)}</span>
              </div>
              {image.taken_at && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Taken</span>
                  <span>{formatDate(image.taken_at)}</span>
                </div>
              )}
              {image.camera_make && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Camera</span>
                  <span>{image.camera_make} {image.camera_model}</span>
                </div>
              )}
            </CardContent>
          </Card>

          {image.categories.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Categories</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {image.categories.map((cat) => (
                    <Badge key={cat} variant="secondary" className="capitalize">
                      {cat}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Status</CardTitle>
            </CardHeader>
            <CardContent>
              <Badge
                variant={
                  image.processing_status === "completed"
                    ? "default"
                    : image.processing_status === "failed"
                    ? "destructive"
                    : "secondary"
                }
                className="capitalize"
              >
                {image.processing_status}
              </Badge>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
