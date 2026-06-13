# Architecture Overview

## System Architecture

PhotoAI is designed as a dual-deployment platform that runs locally via Docker Compose for development and evaluation, and deploys to Google Cloud Platform for production.

### Local Deployment

```
┌──────────────────────────────────────────────────────────────┐
│                      Docker Network                           │
│                                                              │
│  ┌──────────┐   ┌──────────┐   ┌───────────────────────┐   │
│  │ Next.js  │──►│ FastAPI  │──►│  PostgreSQL 16        │   │
│  │ :3000    │   │ :8000    │   │  + pgvector extension │   │
│  └──────────┘   └────┬─────┘   └───────────────────────┘   │
│                      │                                       │
│          ┌───────────┼───────────┐                          │
│          ▼           ▼           ▼                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  Celery  │  │  Redis   │  │  MinIO   │                  │
│  │ Workers  │  │  :6379   │  │  :9000   │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
  ┌──────────────┐              ┌──────────────┐
  │ Vertex AI    │              │ Gemini       │
  │ Embeddings   │              │ Vision API   │
  └──────────────┘              └──────────────┘
```

### Cloud Deployment (GCP)

```
┌─────────────────────────────────────────────────────────┐
│                    Google Cloud Platform                  │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │  Cloud Run   │  │  Cloud Run   │  │  Cloud SQL  │  │
│  │  (Frontend)  │  │  (API)       │  │  PostgreSQL │  │
│  └──────────────┘  └──────┬───────┘  └─────────────┘  │
│                           │                             │
│            ┌──────────────┼──────────────┐             │
│            ▼              ▼              ▼             │
│    ┌────────────┐  ┌────────────┐  ┌──────────┐      │
│    │ Cloud Run  │  │ Memorystore│  │   GCS    │      │
│    │ (Worker)   │  │  (Redis)   │  │ Buckets  │      │
│    └────────────┘  └────────────┘  └──────────┘      │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │  Vertex AI   │  │   Gemini     │  │  Artifact   │  │
│  │  Embeddings  │  │   Vision     │  │  Registry   │  │
│  └──────────────┘  └──────────────┘  └─────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Processing Pipeline

### Image Processing Flow

```
Upload → Preprocess → Fan-Out → Analysis → Complete
                         │
                         ├── Vertex AI Embedding (1408d)
                         ├── Perceptual Hashing (pHash, dHash)
                         └── Face Detection (InsightFace)
                                    │
                                    ├── Gemini Categorization
                                    ├── Duplicate Matching
                                    └── Face Clustering
```

### Processing Stages

1. **Preprocess**: Generate thumbnail (300px), extract EXIF metadata, compute MD5 hash
2. **Embedding**: Generate 1408-dimensional vector via Vertex AI multimodal model
3. **Hashing**: Compute pHash and dHash for perceptual duplicate detection
4. **Face Detection**: InsightFace buffalo_l detects faces, extracts 512d embeddings
5. **Categorization**: Gemini 1.5 Flash classifies into predefined categories
6. **Duplicate Matching**: Compare against existing hashes and embeddings
7. **Face Clustering**: Assign faces to existing clusters or create new ones

## Data Flow

### Search Query Flow

```
User Query (text)
    │
    ▼
Vertex AI Text Embedding (1408d)
    │
    ▼
pgvector Cosine Similarity (HNSW index)
    │
    ▼
Top-K Results with scores
```

### Duplicate Detection Flow

```
New Image
    │
    ├── MD5 → Exact match lookup (O(1))
    │
    ├── pHash → Hamming distance ≤ 8 against all images
    │
    └── Embedding → Cosine similarity > 0.92 via pgvector
```

## Key Design Patterns

### Abstraction Layer Pattern

Environment-driven provider switching enables seamless local/cloud deployment:

```python
# Storage: MinIO (local) ↔ GCS (cloud)
class StorageBackend(ABC):
    async def upload(key, data) -> str
    async def get_presigned_url(key) -> str

# Embeddings: CLIP (fallback) ↔ Vertex AI (primary)
class EmbeddingProvider(ABC):
    async def embed_image(bytes) -> list[float]
    async def embed_text(text) -> list[float]
```

### Scale Strategy

- **pgvector HNSW index**: <10ms approximate nearest neighbor at 100k vectors
- **Cursor-based pagination**: Stable performance regardless of offset
- **Celery chord**: Parallel processing stages with synchronization
- **Presigned URLs**: Direct client-to-storage download, bypassing API
- **Batch processing**: Process up to 50 images concurrently per worker

## Security

- OAuth2 for Google Photos (PKCE flow)
- Presigned URLs for storage access (time-limited)
- CORS configuration per environment
- Service accounts with minimal IAM roles
- VPC peering for Cloud SQL/Redis (no public IP)
