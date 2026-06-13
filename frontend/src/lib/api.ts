import type {
  Image,
  FaceCluster,
  DuplicatePair,
  ProcessingJob,
  StatsOverview,
  SearchResult,
  PaginatedResponse,
  CategoryCount,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  images: {
    list(cursor?: string, limit = 30, category?: string) {
      const params = new URLSearchParams({ limit: String(limit) });
      if (cursor) params.set("cursor", cursor);
      if (category) params.set("category", category);
      return request<PaginatedResponse<Image>>(`/api/v1/images?${params}`);
    },
    get(id: string) {
      return request<Image>(`/api/v1/images/${id}`);
    },
    delete(id: string) {
      return request<void>(`/api/v1/images/${id}`, { method: "DELETE" });
    },
    async upload(files: File[], onProgress?: (pct: number) => void) {
      const formData = new FormData();
      files.forEach((f) => formData.append("files", f));
      const xhr = new XMLHttpRequest();
      return new Promise<Image[]>((resolve, reject) => {
        xhr.upload.addEventListener("progress", (e) => {
          if (e.lengthComputable && onProgress) {
            onProgress(Math.round((e.loaded / e.total) * 100));
          }
        });
        xhr.addEventListener("load", () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(JSON.parse(xhr.responseText));
          } else {
            reject(new Error(`Upload failed: ${xhr.status}`));
          }
        });
        xhr.addEventListener("error", () => reject(new Error("Upload failed")));
        xhr.open("POST", `${API_BASE}/api/v1/images/upload`);
        xhr.send(formData);
      });
    },
  },

  search: {
    query(query: string, limit = 20) {
      return request<SearchResult[]>("/api/v1/search", {
        method: "POST",
        body: JSON.stringify({ query, limit }),
      });
    },
    similar(imageId: string, limit = 10) {
      return request<SearchResult[]>(
        `/api/v1/search/similar/${imageId}?limit=${limit}`
      );
    },
  },

  faces: {
    listClusters() {
      return request<FaceCluster[]>("/api/v1/faces/clusters");
    },
    getClusterImages(clusterId: string, cursor?: string) {
      const params = new URLSearchParams();
      if (cursor) params.set("cursor", cursor);
      return request<PaginatedResponse<Image>>(
        `/api/v1/faces/clusters/${clusterId}/images?${params}`
      );
    },
    renameCluster(clusterId: string, name: string) {
      return request<FaceCluster>(`/api/v1/faces/clusters/${clusterId}`, {
        method: "PATCH",
        body: JSON.stringify({ name }),
      });
    },
    mergeClusters(sourceId: string, targetId: string) {
      return request<FaceCluster>("/api/v1/faces/clusters/merge", {
        method: "POST",
        body: JSON.stringify({ source_id: sourceId, target_id: targetId }),
      });
    },
  },

  duplicates: {
    list(status = "pending") {
      return request<DuplicatePair[]>(`/api/v1/duplicates?status=${status}`);
    },
    resolve(id: string, action: "keep_a" | "keep_b" | "dismiss") {
      return request<void>(`/api/v1/duplicates/${id}/resolve`, {
        method: "POST",
        body: JSON.stringify({ action }),
      });
    },
    scan() {
      return request<ProcessingJob>("/api/v1/duplicates/scan", {
        method: "POST",
      });
    },
  },

  categories: {
    list() {
      return request<{ categories: CategoryCount[]; total_images: number }>("/api/v1/categories")
        .then((res) => res.categories);
    },
    getImages(slug: string, cursor?: string) {
      const params = new URLSearchParams();
      if (cursor) params.set("cursor", cursor);
      return request<PaginatedResponse<Image>>(
        `/api/v1/categories/${slug}/images?${params}`
      );
    },
  },

  googlePhotos: {
    getAuthUrl() {
      return request<{ url: string }>("/api/v1/google-photos/auth-url");
    },
    callback(code: string) {
      return request<void>("/api/v1/google-photos/callback", {
        method: "POST",
        body: JSON.stringify({ code }),
      });
    },
    sync() {
      return request<ProcessingJob>("/api/v1/google-photos/sync", {
        method: "POST",
      });
    },
    status() {
      return request<{ connected: boolean; last_sync: string | null }>(
        "/api/v1/google-photos/status"
      );
    },
  },

  jobs: {
    list() {
      return request<ProcessingJob[]>("/api/v1/jobs");
    },
    get(id: string) {
      return request<ProcessingJob>(`/api/v1/jobs/${id}`);
    },
  },

  stats: {
    overview() {
      return request<StatsOverview>("/api/v1/stats/overview");
    },
  },
};
