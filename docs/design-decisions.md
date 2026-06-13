# Design Decisions

## 1. Vertex AI Multimodal Embeddings over CLIP

**Decision**: Use Vertex AI's `multimodalembedding@001` (1408 dimensions) as the primary embedding model.

**Rationale**:
- Unified image+text embedding space enables natural language search without separate models
- 1408 dimensions provides higher fidelity than CLIP's 512d for similarity matching
- No GPU required locally — API-based, scales with rate limits (600 RPM)
- GCP-native integration simplifies deployment
- CLIP retained as local fallback for offline/no-API scenarios

**Trade-off**: API latency (~200ms per image) vs. local CLIP (~50ms). Mitigated by async batch processing.

## 2. PostgreSQL + pgvector over Pinecone/Weaviate

**Decision**: Use pgvector extension in PostgreSQL rather than a dedicated vector database.

**Rationale**:
- Single database for relational data AND vector search simplifies architecture
- HNSW index achieves <10ms query latency at 100k vectors
- Transactional consistency — embedding stored atomically with image metadata
- No additional infrastructure cost or vendor lock-in
- Cloud SQL supports pgvector natively

**Trade-off**: At 10M+ vectors, a dedicated vector DB might be needed. For 100k target, pgvector is optimal.

## 3. Three-Tier Duplicate Detection

**Decision**: Combine MD5, perceptual hashing, and semantic embeddings for duplicate detection.

**Rationale**:
- **MD5**: Catches exact byte-for-byte duplicates instantly (O(1) index lookup)
- **Perceptual Hash (pHash/dHash)**: Catches crops, resizes, compression changes. Hamming distance ≤ 8 threshold balances precision/recall
- **Embedding Similarity**: Catches semantic duplicates (same scene, different angle). Cosine > 0.92 threshold

Each tier catches duplicates the others miss, providing comprehensive coverage without false positives.

## 4. Incremental Face Clustering

**Decision**: Assign new faces to existing clusters incrementally, with periodic full DBSCAN re-clustering.

**Rationale**:
- O(n) assignment per new face vs. O(n²) full clustering on every upload
- Users see immediate results — faces group within seconds of processing
- Periodic DBSCAN (hourly) corrects drift and merges clusters that should be unified
- Threshold 0.68 cosine similarity balances grouping accuracy with avoiding false merges

**Alternative considered**: Run DBSCAN on every upload — doesn't scale past 10k faces.

## 5. Celery over Cloud Tasks / Pub/Sub

**Decision**: Use Celery with Redis as the task queue for both local and cloud.

**Rationale**:
- Consistent behavior between local Docker and Cloud Run deployments
- Rich task primitives: chains, chords, groups for pipeline orchestration
- Beat scheduler for periodic tasks (re-clustering, sync checks)
- Cloud Tasks doesn't support the complex fan-out patterns needed for the processing pipeline
- Redis (Memorystore in GCP) is already needed for caching

## 6. Next.js App Router + Server-Side Rendering

**Decision**: Next.js 14 with App Router, primarily using client components with React Query.

**Rationale**:
- App Router provides excellent file-based routing structure
- React Query handles caching, pagination, and real-time updates elegantly
- Client-side rendering for interactive features (infinite scroll, real-time progress)
- Standalone output mode enables simple Docker containerization
- API rewrites in next.config.ts avoid CORS issues in development

## 7. MinIO for Local Object Storage

**Decision**: Use MinIO as S3-compatible object storage for local development.

**Rationale**:
- S3 API compatibility means storage code works identically with GCS (via abstraction)
- Presigned URL support matches GCS behavior
- Web console (:9001) for easy debugging
- Lightweight Docker container
- Same abstraction layer (`StorageBackend`) swaps to GCS via single env var

## 8. Gemini 1.5 Flash for Categorization

**Decision**: Use Gemini 1.5 Flash for image categorization over fine-tuned classifiers.

**Rationale**:
- Zero training data needed — works immediately with prompt engineering
- Structured JSON output provides category + confidence in one call
- Cost: ~$0.0001 per image (Flash pricing)
- Easily extensible — add new categories by updating the prompt
- Higher accuracy than zero-shot CLIP on domain-specific categories (prescriptions, receipts)

**Trade-off**: API dependency. Mitigation: graceful degradation to "other" category on API failure.

## 9. Dual-Deployment Architecture

**Decision**: Abstract all infrastructure-dependent code behind interfaces, swap via env vars.

**Rationale**:
- Evaluators can run `docker compose up` with zero cloud credentials
- Production uses managed GCP services for reliability and scale
- Same codebase, same tests — no divergence between environments
- Factory pattern (`get_storage()`, `get_embedding_provider()`) centralizes switching logic

**Abstracted layers**: Storage (MinIO/GCS), Embeddings (CLIP/Vertex AI), Database (same driver), Cache (same Redis protocol).

## 10. WebSocket for Real-Time Progress

**Decision**: WebSocket connection for processing progress updates.

**Rationale**:
- Processing a batch of 100 images takes 2-5 minutes
- Polling would create unnecessary load; SSE doesn't support bidirectional communication
- WebSocket provides instant feedback per-image completion
- Auto-reconnect with exponential backoff handles connection drops
- Single connection multiplexed across all active jobs
