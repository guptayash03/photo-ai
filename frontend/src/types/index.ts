export interface Image {
  id: string;
  original_filename: string;
  thumbnail_url: string | null;
  storage_url?: string | null;
  file_size: number;
  mime_type: string;
  width: number | null;
  height: number | null;
  taken_at: string | null;
  camera_make: string | null;
  camera_model: string | null;
  gps_latitude: number | null;
  gps_longitude: number | null;
  source: string;
  processing_status: string;
  categories: string[];
  created_at: string;
}

export type CategoryType =
  | "document"
  | "prescription"
  | "receipt"
  | "people"
  | "travel"
  | "pet"
  | "food"
  | "nature"
  | "other";

export interface FaceCluster {
  id: string;
  name: string | null;
  face_count: number;
  representative_face_url: string | null;
  created_at: string;
}

export interface Face {
  id: string;
  image_id: string;
  cluster_id: string | null;
  bbox_x: number;
  bbox_y: number;
  bbox_w: number;
  bbox_h: number;
  thumbnail_url: string | null;
  confidence: number;
}

export interface DuplicateImageInfo {
  id: string;
  original_filename: string;
  thumbnail_url: string | null;
  file_size: number;
  width: number | null;
  height: number | null;
}

export interface DuplicatePair {
  id: string;
  image_a: DuplicateImageInfo;
  image_b: DuplicateImageInfo;
  similarity_score: number;
  duplicate_type: string;
  detection_method: string;
  status: string;
  created_at: string;
}

export interface ProcessingJob {
  id: string;
  job_type: string;
  status: "pending" | "running" | "completed" | "failed";
  total_items: number;
  processed_items: number;
  failed_items: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface StatsOverview {
  total_images: number;
  total_processed: number;
  total_pending: number;
  total_faces: number;
  total_people: number;
  total_duplicates: number;
  storage_used_bytes: number;
  category_distribution: CategoryCount[];
  recent_uploads_count: number;
  processing_queue_size: number;
}

export interface CategoryCount {
  name: string;
  count: number;
}

export interface SearchResult {
  image: Image;
  score: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  next_cursor: string | null;
  total: number;
}

export interface WebSocketMessage {
  type: "progress" | "complete" | "error";
  job_id: string;
  data: {
    processed: number;
    total: number;
    current_file?: string;
    message?: string;
  };
}
