#!/bin/bash
set -euo pipefail

PROJECT_ID=${1:-$(gcloud config get-value project 2>/dev/null)}
REGION=${2:-us-central1}

if [ -z "$PROJECT_ID" ]; then
  echo "Usage: ./deploy.sh <project-id> [region]"
  echo "  or set a default project: gcloud config set project <project-id>"
  exit 1
fi

echo "============================================"
echo "  Deploying PhotoAI to GCP"
echo "  Project: $PROJECT_ID"
echo "  Region:  $REGION"
echo "============================================"
echo ""

# Step 1: Enable required APIs
echo ">>> Enabling GCP APIs..."
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
  servicenetworking.googleapis.com \
  --project="$PROJECT_ID" --quiet

echo ">>> APIs enabled."

# Step 2: Apply Terraform (infrastructure only, excluding Cloud Run services)
echo ""
echo ">>> Applying Terraform infrastructure..."
cd "$(dirname "$0")/../terraform"

if [ ! -f "terraform.tfvars" ]; then
  echo "ERROR: terraform/terraform.tfvars not found."
  echo "Copy terraform.tfvars.example and fill in your values."
  exit 1
fi

terraform init -input=false
terraform apply -auto-approve \
  -target=google_project_service.apis \
  -target=google_compute_network.vpc \
  -target=google_compute_global_address.private_ip \
  -target=google_service_networking_connection.private_vpc \
  -target=google_vpc_access_connector.connector \
  -target=google_sql_database_instance.main \
  -target=google_sql_database.db \
  -target=google_sql_user.user \
  -target=google_redis_instance.cache \
  -target=google_storage_bucket.photos \
  -target=google_storage_bucket.thumbnails \
  -target=google_artifact_registry_repository.images \
  -target=google_service_account.api \
  -target=google_service_account.worker \
  -target=google_project_iam_member.api_sql \
  -target=google_project_iam_member.api_storage \
  -target=google_project_iam_member.api_vertex \
  -target=google_project_iam_member.worker_sql \
  -target=google_project_iam_member.worker_storage \
  -target=google_project_iam_member.worker_vertex

cd ..
echo ">>> Infrastructure provisioned."

# Step 3: Configure Docker for Artifact Registry
echo ""
echo ">>> Configuring Docker authentication..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# Step 4: Build and push images via Cloud Build
echo ""
echo ">>> Building and pushing container images..."
gcloud builds submit \
  --config=deploy/cloudbuild.yaml \
  --substitutions="_REGION=${REGION}" \
  --project="$PROJECT_ID" \
  --quiet

echo ">>> Images built and pushed."

# Step 5: Get infrastructure outputs for Cloud Run env vars
echo ""
echo ">>> Reading infrastructure outputs..."
cd terraform
DB_CONNECTION_NAME=$(terraform output -raw db_connection_name 2>/dev/null || echo "")
REDIS_HOST=$(terraform output -raw redis_host 2>/dev/null || echo "")
PHOTOS_BUCKET=$(terraform output -raw photos_bucket 2>/dev/null || echo "")
THUMBNAILS_BUCKET=$(terraform output -raw thumbnails_bucket 2>/dev/null || echo "")
cd ..

DB_PASSWORD=$(grep 'db_password' terraform/terraform.tfvars | sed 's/.*= *"\(.*\)"/\1/')
DB_USER=$(grep 'db_user' terraform/terraform.tfvars | sed 's/.*= *"\(.*\)"/\1/' || echo "postgres")
DB_NAME=$(grep 'db_name' terraform/terraform.tfvars | sed 's/.*= *"\(.*\)"/\1/' || echo "photomanager")

IMAGE_BASE="${REGION}-docker.pkg.dev/${PROJECT_ID}/photoai"

# Step 6: Deploy Cloud Run services
echo ""
echo ">>> Deploying API to Cloud Run..."
gcloud run deploy photoai-api \
  --image="${IMAGE_BASE}/api:latest" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --service-account="photoai-api@${PROJECT_ID}.iam.gserviceaccount.com" \
  --add-cloudsql-instances="$DB_CONNECTION_NAME" \
  --vpc-connector="photoai-connector" \
  --set-env-vars="DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${DB_CONNECTION_NAME}" \
  --set-env-vars="REDIS_URL=redis://${REDIS_HOST}:6379/0" \
  --set-env-vars="STORAGE_BACKEND=gcs" \
  --set-env-vars="GCS_BUCKET_PHOTOS=${PHOTOS_BUCKET}" \
  --set-env-vars="GCS_BUCKET_THUMBNAILS=${THUMBNAILS_BUCKET}" \
  --set-env-vars="EMBEDDING_BACKEND=vertex_ai" \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID}" \
  --set-env-vars="GCP_REGION=${REGION}" \
  --set-env-vars="ALLOWED_ORIGINS=*" \
  --set-env-vars="SECRET_KEY=$(openssl rand -hex 32)" \
  --memory=2Gi \
  --cpu=2 \
  --min-instances=0 \
  --max-instances=10 \
  --project="$PROJECT_ID" \
  --quiet

echo ""
echo ">>> Deploying Worker to Cloud Run..."
gcloud run deploy photoai-worker \
  --image="${IMAGE_BASE}/worker:latest" \
  --region="$REGION" \
  --platform=managed \
  --no-allow-unauthenticated \
  --service-account="photoai-worker@${PROJECT_ID}.iam.gserviceaccount.com" \
  --add-cloudsql-instances="$DB_CONNECTION_NAME" \
  --vpc-connector="photoai-connector" \
  --set-env-vars="DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${DB_CONNECTION_NAME}" \
  --set-env-vars="REDIS_URL=redis://${REDIS_HOST}:6379/0" \
  --set-env-vars="STORAGE_BACKEND=gcs" \
  --set-env-vars="GCS_BUCKET_PHOTOS=${PHOTOS_BUCKET}" \
  --set-env-vars="GCS_BUCKET_THUMBNAILS=${THUMBNAILS_BUCKET}" \
  --set-env-vars="EMBEDDING_BACKEND=vertex_ai" \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID}" \
  --set-env-vars="GCP_REGION=${REGION}" \
  --memory=8Gi \
  --cpu=4 \
  --min-instances=1 \
  --max-instances=5 \
  --project="$PROJECT_ID" \
  --quiet

API_URL=$(gcloud run services describe photoai-api --region="$REGION" --format='value(status.url)' --project="$PROJECT_ID")

echo ""
echo ">>> Deploying Frontend to Cloud Run..."
gcloud run deploy photoai-frontend \
  --image="${IMAGE_BASE}/frontend:latest" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="NEXT_PUBLIC_API_URL=${API_URL}" \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=5 \
  --project="$PROJECT_ID" \
  --quiet

# Step 7: Print deployment info
FRONTEND_URL=$(gcloud run services describe photoai-frontend --region="$REGION" --format='value(status.url)' --project="$PROJECT_ID")

echo ""
echo "============================================"
echo "  Deployment Complete!"
echo "============================================"
echo ""
echo "Frontend: $FRONTEND_URL"
echo "API:      $API_URL"
echo "API Docs: ${API_URL}/docs"
echo ""
echo "Next steps:"
echo "  1. Set OAuth credentials:"
echo "     gcloud run services update photoai-api --region=${REGION} \\"
echo "       --set-env-vars=\"GOOGLE_CLIENT_ID=xxx,GOOGLE_CLIENT_SECRET=xxx\""
echo "  2. Configure Google Photos OAuth redirect URI to:"
echo "     ${API_URL}/api/v1/google-photos/callback"
echo "  3. Update ALLOWED_ORIGINS on API to: ${FRONTEND_URL}"
