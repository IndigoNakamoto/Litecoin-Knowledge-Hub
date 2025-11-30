# Google Cloud Deployment Playbook

## Overview

This playbook provides a step-by-step guide for deploying the Litecoin Knowledge Hub to Google Cloud Platform. Use this for:
1. **Dry run testing** (recommended now)
2. **Staging environment** setup
3. **Production deployment** when traffic justifies it

## 🚀 Quick Start / Recommended Execution Order

**For first-time deployment, follow this optimized sequence:**

### Parallel Execution Strategy (Saves Time)

1. **Foundation Setup** (Sequential - 5 minutes):
   - Run **Step 1** (Create GCP Project)
   - Run **Step 2** (Enable APIs)
   - Run **Step 3** (Artifact Registry)

2. **Long-Running Tasks** (Start these in parallel - 10-15 minutes):
   - **Terminal Tab 1**: Run **Step 4** (`gcloud builds submit`) - This takes 5-10 minutes
   - **Terminal Tab 2**: While builds run, execute **Step 5** (MongoDB Atlas setup) and **Step 6** (Service Accounts & Secrets)

3. **Deployment** (Sequential - 10 minutes):
   - Run **Step 6.5** (FAISS Index decision)
   - Run **Step 7** (Deploy Backend)
   - Run **Step 8** (Deploy Payload CMS)
   - Run **Step 9** (Set up Redis with Direct VPC Egress)

4. **Configuration & Testing** (Sequential - 5 minutes):
   - Run **Step 10** (Custom Domains - optional)
   - Run **Step 11** (Monitoring - optional)
   - Run **Step 12** (Test Deployment)

5. **Cleanup** (If dry run only):
   - Run **Step 13** (Cleanup) - **⚠️ CRITICAL: Don't forget to delete Redis!**

**Total Time**: ~30-40 minutes for complete dry run setup

**Pro Tip**: While Step 4 builds are running, you can complete Steps 5-6 in parallel to save time.

## ⚠️ Critical Notes for M1 Mac Users

**This playbook includes fixes for M1 Mac-specific issues:**

1. **Docker Architecture**: Cloud Run runs on `linux/amd64`. Use **Cloud Build** (recommended) or local builds with `--platform linux/amd64` flag
2. **VPC Connectivity**: Redis Memorystore requires Direct VPC Egress (see Step 9) - no VPC Connector needed
3. **Stateless Containers**: FAISS index handling for ephemeral Cloud Run filesystem (see Step 6.5)

**Without these fixes, deployment will fail in production.**

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] Google Cloud account created
- [ ] Billing enabled (can use free tier for testing)
- [ ] `gcloud` CLI installed and authenticated
  - **Recommended**: Update to latest version to avoid needing `beta` commands: `gcloud components update`
- [ ] Docker images built and tested locally (or use Cloud Build - recommended)
- [ ] Environment variables documented
- [ ] MongoDB Atlas account (or GCP MongoDB)
- [ ] Domain names ready (optional for staging)

## Phase 1: Dry Run Setup (Do This Now)

### Step 1: Create GCP Project

```bash
# Install gcloud CLI if not already installed
# macOS: brew install google-cloud-sdk

# Authenticate
gcloud auth login

# Create new project (or use existing)
gcloud projects create litecoin-knowledge-hub --name="Litecoin Knowledge Hub"

# Set as active project
gcloud config set project litecoin-knowledge-hub

# Enable billing (required for Cloud Run)
# Do this via: https://console.cloud.google.com/billing
```

### Step 2: Enable Required APIs

```bash
# Enable Cloud Run API
gcloud services enable run.googleapis.com

# Enable Cloud Build API (for building images)
gcloud services enable cloudbuild.googleapis.com

# Enable Artifact Registry API (for storing images)
gcloud services enable artifactregistry.googleapis.com

# Enable Secret Manager API (for storing secrets)
gcloud services enable secretmanager.googleapis.com

# Enable Cloud Monitoring API
gcloud services enable monitoring.googleapis.com

# Enable Cloud Logging API
gcloud services enable logging.googleapis.com
```

### Step 3: Set Up Artifact Registry

```bash
# Create repository for Docker images
gcloud artifacts repositories create litecoin-hub \
  --repository-format=docker \
  --location=us-central1 \
  --description="Docker images for Litecoin Knowledge Hub"

# Configure Docker to use gcloud as credential helper
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### Step 4: Build and Push Docker Images

**⚠️ Critical for M1 Mac Users**: Cloud Run runs on `linux/amd64`, but M1 Macs build `linux/arm64` by default. You have two options:

#### Option A: Cloud Build (Recommended - Faster)

**Why**: Docker emulation on M1 Macs is slow, and pushing large images (2GB+) from home internet is unreliable. Cloud Build runs on Google's high-speed servers and automatically builds for `linux/amd64`.

```bash
# From project root
cd /Users/indigo/Dev/Litecoin-Knowledge-Hub

# Build and push backend image using Cloud Build
cd backend
gcloud builds submit --tag us-central1-docker.pkg.dev/litecoin-knowledge-hub/litecoin-hub/backend:latest .

# Build and push Payload CMS image using Cloud Build
cd ../payload_cms
gcloud builds submit --tag us-central1-docker.pkg.dev/litecoin-knowledge-hub/litecoin-hub/payload-cms:latest .
```

#### Option B: Local Build (Slower but Works)

If you prefer local builds, you **must** use the `--platform linux/amd64` flag:

```bash
# From project root
cd /Users/indigo/Dev/Litecoin-Knowledge-Hub

# Build backend image (FORCE AMD64 for Cloud Run compatibility)
cd backend
docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/litecoin-knowledge-hub/litecoin-hub/backend:latest .
docker push us-central1-docker.pkg.dev/litecoin-knowledge-hub/litecoin-hub/backend:latest

# Build Payload CMS image (FORCE AMD64 for Cloud Run compatibility)
cd ../payload_cms
docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/litecoin-knowledge-hub/litecoin-hub/payload-cms:latest .
docker push us-central1-docker.pkg.dev/litecoin-knowledge-hub/litecoin-hub/payload-cms:latest
```

**Recommendation**: Use **Option A (Cloud Build)** for faster, more reliable builds. Cloud Build automatically handles architecture compatibility.

### Step 5: Set Up MongoDB Atlas

```bash
# 1. Go to https://cloud.mongodb.com
# 2. Create new cluster (M10 for production, M0 for testing)
# 3. Create database user
# 4. Whitelist IP addresses (0.0.0.0/0 for Cloud Run)
# 5. Get connection string
# 6. Store in Secret Manager (see next step)
```

### Step 6: Create Service Accounts and Store Secrets

**⚠️ Security Best Practice**: Create dedicated service accounts with minimal permissions instead of using the default Compute Engine service account (which has broad Editor permissions).

```bash
# Create dedicated service accounts for each service
gcloud iam service-accounts create litecoin-backend-sa \
  --display-name="Litecoin Backend Service Account"

gcloud iam service-accounts create litecoin-payload-sa \
  --display-name="Litecoin Payload CMS Service Account"

# Store MongoDB URI
echo -n "mongodb+srv://user:pass@cluster.mongodb.net/litecoin_rag_db" | \
  gcloud secrets create mongo-uri --data-file=-

# Store Google API Key
echo -n "your-google-api-key" | \
  gcloud secrets create google-api-key --data-file=-

# Store Payload Secret
echo -n "your-payload-secret" | \
  gcloud secrets create payload-secret --data-file=-

# Store Webhook Secret
echo -n "your-webhook-secret" | \
  gcloud secrets create webhook-secret --data-file=-

# Grant backend service account access to secrets
PROJECT_ID="litecoin-knowledge-hub"
gcloud secrets add-iam-policy-binding mongo-uri \
  --member="serviceAccount:litecoin-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding google-api-key \
  --member="serviceAccount:litecoin-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding webhook-secret \
  --member="serviceAccount:litecoin-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Grant Payload CMS service account access to secrets
gcloud secrets add-iam-policy-binding mongo-uri \
  --member="serviceAccount:litecoin-payload-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding payload-secret \
  --member="serviceAccount:litecoin-payload-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# If using GCS for FAISS index, grant Storage Object Viewer role
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:litecoin-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"
```

**Why This Matters**: If your app is compromised, a dedicated service account limits the attacker's access to only the specific resources your app needs, rather than broad Editor permissions.

### Step 6.5: Handle FAISS Index (Stateless Container Issue)

**⚠️ Critical**: Cloud Run containers are **ephemeral** - the filesystem is wiped on every restart. Your FAISS index file will not persist.

**Options**:

#### Option A: Rebuild from MongoDB on Startup (Recommended for Small Datasets)
**Best for**: Datasets with <10k chunks

Your backend should already handle this - ensure `backend/rag_pipeline.py` rebuilds the index from MongoDB if the local file doesn't exist.

**Pros**: Simple, no additional infrastructure
**Cons**: Slow cold starts (45+ seconds) if dataset is large

**For Dry Run**: Use this option - it's the simplest and works immediately.

#### Option B: Bake Index into Docker Image (Recommended for Stable Indexes)
**Best for**: Indexes that don't change hourly

If your index is relatively stable, bake it into the Docker image during build:

```bash
# During Docker build, copy index files into image
# In your Dockerfile:
COPY faiss_index/ /app/backend/faiss_index/
```

**Pros**: Instant startup, no network download
**Cons**: Larger image size, requires rebuild when index changes

#### Option C: Store in Google Cloud Storage (Use with Caution)
**Best for**: Large, frequently-updated indexes

**⚠️ Warning**: Downloading a 500MB index from GCS on every cold start can be slower than rebuilding from MongoDB for small datasets.

```bash
# Create GCS bucket for FAISS index
gsutil mb -p litecoin-knowledge-hub -l us-central1 gs://litecoin-faiss-index

# Upload existing index (if you have one)
gsutil cp backend/faiss_index/index.faiss gs://litecoin-faiss-index/
gsutil cp backend/faiss_index/index.pkl gs://litecoin-faiss-index/

# Update backend to download from GCS on startup
# Add to startup script (not Dockerfile):
# gsutil cp gs://litecoin-faiss-index/* /app/backend/faiss_index/
```

**Pros**: Works for large indexes, can update without rebuilding image
**Cons**: Adds network latency to cold starts, requires GCS permissions

#### Option D: Use MongoDB Atlas Vector Search Only (Ideal Long-Term)
**Best for**: Production deployments

If your backend supports it, disable local FAISS and use MongoDB Atlas Vector Search exclusively.

**Pros**: 
- Removes memory burden from Cloud Run (can drop from 4Gi to 2Gi RAM, saving ~50% on compute costs)
- No cold start penalty
- Scales automatically with MongoDB

**Cons**: Requires MongoDB Atlas Vector Search setup

**Recommendation**: 
- **Short Term**: Use Option A for dry run testing
- **Long Term**: Migrate to Option D (MongoDB Vector Search) to reduce costs and eliminate cold start issues

### Step 7: Deploy Backend to Cloud Run

```bash
# Deploy backend service with dedicated service account
gcloud run deploy backend \
  --image us-central1-docker.pkg.dev/litecoin-knowledge-hub/litecoin-hub/backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --service-account litecoin-backend-sa@litecoin-knowledge-hub.iam.gserviceaccount.com \
  --memory 4Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0 \
  --set-env-vars "NODE_ENV=production" \
  --set-secrets "MONGO_URI=mongo-uri:latest,GOOGLE_API_KEY=google-api-key:latest,WEBHOOK_SECRET=webhook-secret:latest" \
  --set-env-vars "CORS_ORIGINS=https://your-frontend-domain.com" \
  --set-env-vars "DAILY_SPEND_LIMIT_USD=10.00" \
  --set-env-vars "HOURLY_SPEND_LIMIT_USD=3.00" \
  --set-env-vars "HIGH_COST_THRESHOLD_USD=0.015" \
  --set-env-vars "RATE_LIMIT_PER_MINUTE=60" \
  --set-env-vars "RATE_LIMIT_PER_HOUR=100"

# Get the service URL
BACKEND_URL=$(gcloud run services describe backend --platform managed --region us-central1 --format 'value(status.url)')
echo "Backend URL: $BACKEND_URL"
```

**Note**: The `--service-account` flag uses the dedicated service account created in Step 6, which has minimal permissions for better security.

### Step 8: Deploy Payload CMS to Cloud Run

```bash
# Deploy Payload CMS service with dedicated service account
gcloud run deploy payload-cms \
  --image us-central1-docker.pkg.dev/litecoin-knowledge-hub/litecoin-hub/payload-cms:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --service-account litecoin-payload-sa@litecoin-knowledge-hub.iam.gserviceaccount.com \
  --memory 2Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 5 \
  --min-instances 0 \
  --set-secrets "DATABASE_URI=mongo-uri:latest,PAYLOAD_SECRET=payload-secret:latest" \
  --set-env-vars "NODE_ENV=production" \
  --set-env-vars "PAYLOAD_PUBLIC_SERVER_URL=https://payload-cms-xxxxx.run.app"

# Get the service URL
PAYLOAD_URL=$(gcloud run services describe payload-cms --platform managed --region us-central1 --format 'value(status.url)')
echo "Payload CMS URL: $PAYLOAD_URL"
```

**Note**: The `--service-account` flag uses the dedicated service account created in Step 6, which has minimal permissions for better security.

### Step 9: Set Up Redis (Memorystore) with Direct VPC Egress

**⚠️ Critical**: Redis Memorystore uses a **private IP** within a VPC. Cloud Run needs **Direct VPC Egress** to access it.

**Modern Approach**: Use **Direct VPC Egress** instead of a VPC Connector. This is cheaper (no 24/7 VM costs) and easier to set up.

```bash
# Create Redis instance
gcloud redis instances create litecoin-redis \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_7_0 \
  --tier=basic \
  --network=default

# Wait for Redis to be ready (takes 5-10 minutes)
echo "Waiting for Redis instance to be ready..."
gcloud redis instances describe litecoin-redis --region=us-central1 --format='value(state)'
# Wait until state is "READY"

# Get Redis IP address (this is a private IP in the VPC)
REDIS_IP=$(gcloud redis instances describe litecoin-redis --region=us-central1 --format='value(host)')
echo "Redis IP: $REDIS_IP"

# Update backend service to use Direct VPC Egress and Redis
# ⚠️ Note: If you get "unrecognized flag" error, use 'beta' prefix (see troubleshooting)
gcloud run services update backend \
  --vpc-egress=private-ranges-only \
  --network=default \
  --subnet=default \
  --set-env-vars "REDIS_HOST=$REDIS_IP,REDIS_PORT=6379" \
  --region=us-central1

# If the above command fails with "unrecognized flag: --network", use beta version:
# gcloud beta run services update backend \
#   --vpc-egress=private-ranges-only \
#   --network=default \
#   --subnet=default \
#   --set-env-vars "REDIS_HOST=$REDIS_IP,REDIS_PORT=6379" \
#   --region=us-central1
```

**Why Direct VPC Egress Instead of VPC Connector?**
- **Cost**: VPC Connectors require dedicated VM instances running 24/7 (~$17/month minimum), even with zero traffic
- **Simplicity**: Direct VPC Egress requires no connector setup - just network configuration
- **Performance**: Direct connection without an extra hop through connector VMs
- **Cost Savings**: You only pay for data processing, not idle VMs

**Alternative: VPC Connector (If Direct VPC Egress Not Available)**
If Direct VPC Egress is not available in your region or you need the connector for other reasons:

```bash
# Enable VPC Access API
gcloud services enable vpcaccess.googleapis.com

# Create VPC Connector
gcloud compute networks vpc-access connectors create litecoin-connector \
  --region=us-central1 \
  --range=10.8.0.0/28 \
  --network=default \
  --min-instances=2 \
  --max-instances=3

# Update service to use connector
gcloud run services update backend \
  --vpc-connector=litecoin-connector \
  --vpc-egress=private-ranges-only \
  --region=us-central1
```

**Note**: This adds ~$17/month in fixed costs. Direct VPC Egress is preferred when available.

**Alternative for Staging/Testing**: If you want to save the $35/month Redis Memorystore cost for staging, you can run Redis on a small VM (f1-micro) for ~$5/month, or use a Docker container on Cloud Run (though this has limitations).

**Why This Matters**: Without Direct VPC Egress (or VPC Connector), Cloud Run cannot reach Redis Memorystore's private IP, causing connection timeouts and cache failures.

### Step 10: Configure Custom Domains (Optional)

```bash
# Map custom domain to backend
gcloud run domain-mappings create \
  --service backend \
  --domain api.yourdomain.com \
  --region us-central1

# Map custom domain to Payload CMS
gcloud run domain-mappings create \
  --service payload-cms \
  --domain cms.yourdomain.com \
  --region us-central1

# Follow DNS instructions provided by gcloud
```

### Step 11: Set Up Monitoring

```bash
# Create alerting policy for high error rate
gcloud alpha monitoring policies create \
  --notification-channels=YOUR_CHANNEL_ID \
  --display-name="High Error Rate" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s

# Create alerting policy for high cost
gcloud alpha monitoring policies create \
  --notification-channels=YOUR_CHANNEL_ID \
  --display-name="High LLM Cost" \
  --condition-threshold-value=10.0
```

### Step 12: Test the Deployment

```bash
# Test backend health endpoint
curl https://backend-xxxxx.run.app/health

# Test backend API
curl https://backend-xxxxx.run.app/api/v1/chat/stream \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Litecoin?", "chat_history": []}'

# Test Payload CMS
curl https://payload-cms-xxxxx.run.app/api/suggested-questions
```

**⚠️ First Request Note**: If you receive a "500 Internal Server Error" or timeout on the **first request**, don't panic. This is normal behavior:

- **Why**: The container is initializing FAISS index from MongoDB (takes 5-10 seconds on first cold start)
- **Fix**: Simply run the `curl` command **a second time**. The container will be "warm" and the response should be instant
- **Expected**: First request: 5-10 seconds, Subsequent requests: < 2 seconds

This is especially common if you're using **Option A** (Rebuild from MongoDB) for FAISS index handling (see Step 6.5).

### Step 13: Cleanup After Dry Run (IMPORTANT)

**⚠️ Critical Cost Warning**: If you're doing a dry run and plan to delete the Cloud Run services, you **must** also delete the Redis instance. Redis Memorystore charges ~$35/month (~$1+ per day) even when not in use.

```bash
# Delete Cloud Run services (if testing only)
gcloud run services delete backend --region=us-central1
gcloud run services delete payload-cms --region=us-central1

# ⚠️ CRITICAL: Delete Redis instance to avoid ongoing charges
gcloud redis instances delete litecoin-redis --region=us-central1

# Optional: Delete secrets (if you want a clean slate)
gcloud secrets delete mongo-uri
gcloud secrets delete google-api-key
gcloud secrets delete payload-secret
gcloud secrets delete webhook-secret

# Optional: Delete service accounts
gcloud iam service-accounts delete litecoin-backend-sa@litecoin-knowledge-hub.iam.gserviceaccount.com
gcloud iam service-accounts delete litecoin-payload-sa@litecoin-knowledge-hub.iam.gserviceaccount.com
```

**Why This Matters**: Redis Memorystore is a persistent resource that continues billing even if your Cloud Run services are deleted. Forgetting to delete it after a dry run can result in unexpected charges.

## Phase 2: Production Deployment Checklist

When traffic justifies migration, follow this checklist:

### Pre-Deployment

- [ ] **Traffic threshold met**: Consistently > 3,000 users/day
- [ ] **Hardware limits hit**: CPU > 70%, Memory > 12GB
- [ ] **Budget approved**: $80-120/month baseline + variable costs for cloud deployment
- [ ] **Dry run completed**: Staging environment tested
- [ ] **Backup created**: Mac Mini data backed up
- [ ] **DNS ready**: Domain names configured
- [ ] **Team notified**: Stakeholders informed

### Deployment Day

- [ ] **Deploy backend** to Cloud Run
- [ ] **Deploy Payload CMS** to Cloud Run
- [ ] **Set up Redis** Memorystore
- [ ] **Configure MongoDB Atlas** connection
- [ ] **Update DNS** records
- [ ] **Update frontend** environment variables
- [ ] **Test all endpoints**
- [ ] **Monitor metrics** closely
- [ ] **Set up alerts**

### Post-Deployment

- [ ] **Monitor for 24 hours**: Watch for issues
- [ ] **Compare performance**: Mac Mini vs Cloud Run
- [ ] **Verify costs**: Check billing dashboard
- [ ] **Update documentation**: Record new URLs/configs
- [ ] **Keep Mac Mini running**: As backup for 1-2 weeks
- [ ] **Gradual traffic shift**: Move traffic incrementally

## Quick Deployment Script

Create `scripts/deploy-gcp.sh`:

**⚠️ Prerequisites**: 
- Redis Memorystore must be created and IP configured (see Step 9)
- Service accounts must be created (see Step 6)
- Secrets must be stored in Secret Manager (see Step 6)

```bash
#!/bin/bash
set -e

PROJECT_ID="litecoin-knowledge-hub"
REGION="us-central1"
REPO="litecoin-hub"

echo "🚀 Deploying to Google Cloud..."

# Build and push images using Cloud Build (recommended - faster than local builds)
echo "📦 Building images with Cloud Build..."
cd backend
gcloud builds submit --tag us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:latest .

cd ../payload_cms
gcloud builds submit --tag us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO}/payload-cms:latest .

# Get Redis IP (must be created first)
REDIS_IP=$(gcloud redis instances describe litecoin-redis --region=${REGION} --format='value(host)')

# Deploy services
echo "🚀 Deploying backend..."
# Note: If you get "unrecognized flag" error, replace 'gcloud run' with 'gcloud beta run'
gcloud run deploy backend \
  --image us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:latest \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --service-account litecoin-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --memory 4Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --vpc-egress=private-ranges-only \
  --network=default \
  --subnet=default \
  --set-env-vars "REDIS_HOST=${REDIS_IP},REDIS_PORT=6379"

echo "🚀 Deploying Payload CMS..."
gcloud run deploy payload-cms \
  --image us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO}/payload-cms:latest \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --service-account litecoin-payload-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --memory 2Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 5

echo "✅ Deployment complete!"
echo ""
echo "⚠️  Important Notes:"
echo "   - Redis Memorystore must be created before first deployment (see Step 9)"
echo "   - Service accounts must be created and granted permissions (see Step 6)"
echo "   - All images built with Cloud Build (automatically linux/amd64 compatible)"
echo "   - If '--network' flag fails, use 'gcloud beta run' instead"
echo ""
echo "⚠️  CRITICAL: After dry runs, delete Redis to avoid ongoing charges:"
echo "   gcloud redis instances delete litecoin-redis --region=${REGION}"
```

## Cost Monitoring

### Fixed Cost Breakdown

**Baseline Monthly Costs** (before any user traffic):

1. **Redis Memorystore (Basic Tier)**: ~$35/month (Fixed, regardless of traffic)
   - **⚠️ WARNING**: This charges ~$1+ per day even if Cloud Run services are deleted
   - **Must delete manually** after dry runs: `gcloud redis instances delete litecoin-redis --region=us-central1`
2. **Cloud Run (Idle)**: $0 (if `min-instances=0`)
3. **Cloud Run (Warm)**: If you set `min-instances=1` to avoid cold starts:
   - 1 vCPU / 4GB RAM running 24/7 = ~$30-40/month
4. **Artifact Registry**: ~$0.10/GB/month (minimal for small images)
5. **Secret Manager**: $0.06/secret/month (4 secrets = ~$0.24/month)

**Total Baseline**: ~$65-75/month (with `min-instances=0`) or ~$95-115/month (with `min-instances=1`)

**⚠️ Critical Cost Trap**: Redis Memorystore is a persistent resource. If you delete Cloud Run services but forget to delete Redis, you'll be charged ~$35/month indefinitely. Always delete Redis after dry runs (see Step 13).

**Cost Optimization Tips**:
- **Staging/Testing**: Use Redis on a VM (f1-micro) instead of Memorystore to save ~$30/month
- **Production**: Consider MongoDB Atlas Vector Search to reduce Cloud Run memory from 4Gi to 2Gi, saving ~50% on compute costs
- **Cold Starts**: If acceptable, keep `min-instances=0` to save ~$30-40/month

### Set Up Billing Alerts

```bash
# Create budget
gcloud billing budgets create \
  --billing-account=YOUR_BILLING_ACCOUNT_ID \
  --display-name="Litecoin Hub Monthly Budget" \
  --budget-amount=200USD \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

### Monitor Costs

```bash
# View current costs
gcloud billing accounts list
gcloud billing projects describe litecoin-knowledge-hub

# View Cloud Run costs
gcloud logging read "resource.type=cloud_run_revision" --limit=50

# View detailed cost breakdown
gcloud billing accounts list
gcloud billing budgets list --billing-account=YOUR_BILLING_ACCOUNT_ID
```

## Rollback Plan

If deployment fails:

1. **Keep Mac Mini running** during migration
2. **Update DNS** to point back to Mac Mini
3. **Monitor** both environments
4. **Fix issues** in Cloud Run
5. **Re-deploy** when ready

## Migration Strategy

### Option 1: Big Bang (Not Recommended)
- Switch all traffic at once
- Risk: High downtime if issues occur
- Use only if: Staging thoroughly tested

### Option 2: Gradual Migration (Recommended)
1. **Week 1**: Deploy to Cloud Run, test with 10% traffic
2. **Week 2**: Increase to 50% traffic, monitor
3. **Week 3**: Move to 100% traffic
4. **Week 4**: Decommission Mac Mini (keep as backup)

### Option 3: Blue-Green Deployment
1. Run both Mac Mini and Cloud Run simultaneously
2. Use load balancer to split traffic
3. Gradually shift traffic
4. Monitor both environments

## Troubleshooting

### Common Issues

**Issue**: Service won't start - "Exec format error"
```bash
# Symptom: Container crashes immediately with "Exec format error"
# Root Cause: Built ARM64 image on M1 Mac, Cloud Run needs AMD64

# Solution: Rebuild with --platform flag
docker build --platform linux/amd64 -t [image] .

# Prevention: Always use --platform linux/amd64 for Cloud Run
```

**Issue**: Redis connection timeouts
```bash
# Symptom: Cannot connect to Redis, connection timeouts
# Root Cause: Cloud Run cannot reach VPC resources without Direct VPC Egress

# Solution: Configure Direct VPC Egress (no connector needed)
# If you get "unrecognized flag" error, use 'beta' prefix:
gcloud run services update backend \
  --vpc-egress=private-ranges-only \
  --network=default \
  --subnet=default \
  --region=us-central1

# Alternative if above fails (use beta):
# gcloud beta run services update backend \
#   --vpc-egress=private-ranges-only \
#   --network=default \
#   --subnet=default \
#   --region=us-central1

# Verify: Check service configuration
gcloud run services describe backend --region=us-central1 --format='value(spec.template.spec.containers[0].env)'

# Verify Redis is accessible
REDIS_IP=$(gcloud redis instances describe litecoin-redis --region=us-central1 --format='value(host)')
echo "Redis IP: $REDIS_IP"
```

**Issue**: "Unrecognized flag" error when using `--network` flag
```bash
# Symptom: gcloud run services update fails with "unrecognized flag: --network"
# Root Cause: Direct VPC Egress may require 'beta' command in older gcloud CLI versions

# Solution: Use beta command
gcloud beta run services update backend \
  --vpc-egress=private-ranges-only \
  --network=default \
  --subnet=default \
  --region=us-central1

# Or update gcloud CLI to latest version
gcloud components update
```

**Issue**: Service won't start
```bash
# Check logs
gcloud run services logs read backend --region us-central1 --limit 50

# Check service status
gcloud run services describe backend --region us-central1

# Check container startup logs
gcloud run services logs read backend --region us-central1 | grep -i error
```

**Issue**: Secrets not accessible
```bash
# Verify IAM permissions for dedicated service account
PROJECT_ID="litecoin-knowledge-hub"
gcloud projects get-iam-policy ${PROJECT_ID}

# Grant access to backend service account
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:litecoin-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Grant access to Payload CMS service account
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:litecoin-payload-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Verify service account is attached to Cloud Run service
gcloud run services describe backend --region=us-central1 --format='value(spec.template.spec.serviceAccountName)'
```

**Issue**: FAISS index missing on startup
```bash
# Symptom: Slow cold starts, index rebuild errors
# Root Cause: Ephemeral filesystem, index not persisted

# Solution A: Ensure backend rebuilds from MongoDB (should be automatic)
# Check logs for index rebuild messages

# Solution B: Upload to GCS and download on startup
gsutil mb -p litecoin-knowledge-hub -l us-central1 gs://litecoin-faiss-index
gsutil cp backend/faiss_index/* gs://litecoin-faiss-index/
# Then modify startup script to download from GCS
```

**Issue**: High costs
```bash
# Check resource usage
gcloud run services describe backend --region us-central1

# Reduce instances
gcloud run services update backend \
  --max-instances 5 \
  --region us-central1

# Check actual costs
gcloud billing accounts list
gcloud billing projects describe litecoin-knowledge-hub
```

**Issue**: Slow cold starts (48+ seconds)
```bash
# Symptom: First request after idle timeout is very slow
# Root Cause: FAISS index rebuild from MongoDB takes 45s

# Solution: Set minimum instances to keep warm
gcloud run services update backend \
  --min-instances=1 \
  --region us-central1

# Or migrate index to GCS for faster startup (see FAISS index issue above)
```

## Maintenance

### Regular Tasks

- **Weekly**: Review costs and usage
- **Monthly**: Update Docker images
- **Quarterly**: Review and optimize resources
- **As needed**: Scale up/down based on traffic

### Updates

```bash
# Update backend using Cloud Build (recommended)
cd backend
gcloud builds submit --tag us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:latest .
gcloud run services update backend \
  --image us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:latest \
  --region us-central1

# Or update using local build (slower, requires --platform flag on M1 Macs)
cd backend
docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:latest .
docker push us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:latest
gcloud run services update backend \
  --image us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:latest \
  --region us-central1
```

## Success Criteria

Deployment is successful when:

- ✅ All services deployed and running
- ✅ Health checks passing
- ✅ Response times < 2 seconds
- ✅ Error rate < 1%
- ✅ Costs within budget
- ✅ Monitoring/alerts configured
- ✅ DNS configured correctly
- ✅ Frontend connecting to new backend

## Next Steps After Deployment

1. **Monitor closely** for first 48 hours
2. **Compare metrics** with Mac Mini baseline
3. **Optimize resources** based on actual usage
4. **Set up auto-scaling** if needed
5. **Document learnings** for future deployments

## References

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Run Pricing](https://cloud.google.com/run/pricing)
- [MongoDB Atlas Setup](https://www.mongodb.com/docs/atlas/getting-started/)
- [Capacity Planning Guide](../planning/CAPACITY_PLANNING.md)
- [Cloud Deployment Readiness](./CLOUD_DEPLOYMENT_READINESS.md)

