# GCP Setup Guide

Complete guide to deploying PhotoAI on Google Cloud Platform.

## Prerequisites

- Google Cloud account with billing enabled
- `gcloud` CLI installed and authenticated
- Terraform >= 1.5 installed
- Docker installed (for building images)

## Step 1: Create GCP Project

```bash
# Create a new project
gcloud projects create photoai-project --name="PhotoAI"

# Set as active project
gcloud config set project photoai-project

# Enable billing (required for Cloud Run, AI services)
# Do this via the Cloud Console: https://console.cloud.google.com/billing
```

## Step 2: Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  vpcaccess.googleapis.com \
  secretmanager.googleapis.com \
  compute.googleapis.com \
  servicenetworking.googleapis.com
```

## Step 3: Configure OAuth (Google Photos)

1. Go to [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)
2. Click **Configure Consent Screen**
   - User Type: External
   - App name: PhotoAI
   - Scopes: `photoslibrary.readonly`
3. Click **Create Credentials > OAuth 2.0 Client ID**
   - Application type: Web application
   - Authorized redirect URIs: `https://photoai-api-<hash>.run.app/api/v1/google-photos/callback`
   - (You'll update this URI after deployment)
4. Note down `Client ID` and `Client Secret`

## Step 4: Terraform Setup

```bash
cd terraform

# Copy example vars
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
# Required: project_id, db_password
# Optional: region (defaults to us-central1)
```

**terraform.tfvars**:
```hcl
project_id  = "photoai-project"
region      = "us-central1"
db_password = "your-secure-password-here"
```

## Step 5: Deploy Infrastructure

```bash
cd terraform
terraform init
terraform plan    # Review what will be created
terraform apply   # Create all resources (~10 minutes)
```

This creates:
- VPC with private networking
- Cloud SQL PostgreSQL 16 instance (pgvector enabled)
- Memorystore Redis instance
- GCS buckets (photos + thumbnails)
- Artifact Registry for Docker images
- VPC Access Connector
- Service accounts with appropriate IAM roles
- Cloud Run services (API, Worker, Frontend)

## Step 6: Build and Deploy Images

### Option A: Automated (Cloud Build)

```bash
# From project root
gcloud builds submit --config=deploy/cloudbuild.yaml \
  --substitutions="_REGION=us-central1"
```

### Option B: One-Command Script

```bash
./deploy/deploy.sh photoai-project us-central1
```

### Option C: Manual

```bash
REGION=us-central1
PROJECT_ID=photoai-project

# Authenticate Docker
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build and push API
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/photoai/api:latest ./backend
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/photoai/api:latest

# Build and push Worker
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/photoai/worker:latest -f ./backend/Dockerfile.worker ./backend
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/photoai/worker:latest

# Build and push Frontend
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/photoai/frontend:latest ./frontend
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/photoai/frontend:latest

# Deploy services
gcloud run deploy photoai-api --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/photoai/api:latest --region=${REGION} --allow-unauthenticated
gcloud run deploy photoai-worker --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/photoai/worker:latest --region=${REGION} --no-allow-unauthenticated
gcloud run deploy photoai-frontend --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/photoai/frontend:latest --region=${REGION} --allow-unauthenticated
```

## Step 7: Run Database Migrations

```bash
# Create a Cloud Run job for migrations
gcloud run jobs create photoai-migrate \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/photoai/api:latest \
  --region=${REGION} \
  --command="alembic" \
  --args="upgrade,head" \
  --set-env-vars="DATABASE_URL=postgresql+asyncpg://postgres:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${CONNECTION_NAME}"

# Execute the migration
gcloud run jobs execute photoai-migrate --region=${REGION} --wait
```

## Step 8: Configure Environment Variables

Set these on the Cloud Run API service:

```bash
gcloud run services update photoai-api --region=${REGION} \
  --set-env-vars="GOOGLE_CLIENT_ID=your-client-id" \
  --set-env-vars="GOOGLE_CLIENT_SECRET=your-client-secret" \
  --set-env-vars="SECRET_KEY=$(openssl rand -hex 32)" \
  --set-env-vars="GOOGLE_REDIRECT_URI=https://photoai-api-xxxx.run.app/api/v1/google-photos/callback"
```

## Step 9: Update OAuth Redirect URI

After deployment, get the API URL:
```bash
gcloud run services describe photoai-api --region=${REGION} --format='value(status.url)'
```

Go back to [OAuth Credentials](https://console.cloud.google.com/apis/credentials) and update the redirect URI to:
`https://<api-url>/api/v1/google-photos/callback`

## Step 10: Verify Deployment

```bash
# Get service URLs
API_URL=$(gcloud run services describe photoai-api --region=${REGION} --format='value(status.url)')
FRONTEND_URL=$(gcloud run services describe photoai-frontend --region=${REGION} --format='value(status.url)')

# Test API health
curl ${API_URL}/api/health

# Open frontend
echo "Frontend: ${FRONTEND_URL}"
echo "API Docs: ${API_URL}/docs"
```

## Cost Estimate (Monthly)

| Service | Specification | Est. Cost |
|---------|--------------|-----------|
| Cloud SQL | db-custom-2-4096, always-on | ~$50 |
| Memorystore | 1GB Basic | ~$35 |
| Cloud Run (API) | 0-10 instances | ~$5-20 |
| Cloud Run (Worker) | 1-5 instances | ~$20-50 |
| GCS | Per GB stored | ~$0.02/GB |
| Vertex AI | Per 1k embeddings | ~$0.01/1k |
| Gemini Flash | Per 1k images | ~$0.10/1k |

**Total estimate**: ~$120-170/month for moderate usage.

## Troubleshooting

### Cloud Run service won't start
- Check logs: `gcloud run services logs read photoai-api --region=${REGION}`
- Verify VPC connector is in same region
- Ensure service account has Cloud SQL Client role

### Database connection refused
- Confirm Cloud SQL instance is running: `gcloud sql instances describe photoai-db`
- Check VPC peering: `gcloud compute networks peerings list`
- Verify the connection name format: `project:region:instance`

### Vertex AI permission denied
- Add AI Platform User role: `gcloud projects add-iam-policy-binding ${PROJECT_ID} --member=serviceAccount:photoai-worker@${PROJECT_ID}.iam.gserviceaccount.com --role=roles/aiplatform.user`

### Image upload fails
- Check GCS bucket exists and service account has Storage Object Admin
- Verify CORS is configured on the bucket
