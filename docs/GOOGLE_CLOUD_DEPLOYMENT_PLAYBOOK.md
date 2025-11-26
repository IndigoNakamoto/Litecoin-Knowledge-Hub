# Google Cloud Deployment Playbook

## Overview

This playbook provides a step-by-step guide for deploying the Litecoin Knowledge Hub to Google Cloud Platform. Use this for:
1. **Dry run testing** (recommended now)
2. **Staging environment** setup
3. **Production deployment** when traffic justifies it

## ⚠️ Critical Notes for M1 Mac Users

**This playbook includes fixes for M1 Mac-specific issues:**

1. **Docker Architecture**: All builds use `--platform linux/amd64` to ensure Cloud Run compatibility
2. **VPC Connectivity**: Redis Memorystore requires VPC Connector setup (see Step 9)
3. **Stateless Containers**: FAISS index handling for ephemeral Cloud Run filesystem (see Step 6.5)

**Without these fixes, deployment will fail in production.**

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] Google Cloud account created
- [ ] Billing enabled (can use free tier for testing)
- [ ] `gcloud` CLI installed and authenticated
- [ ] Docker images built and tested locally
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

**⚠️ Critical for M1 Mac Users**: Cloud Run runs on `linux/amd64`, but M1 Macs build `linux/arm64` by default. You **must** force AMD64 builds or containers will crash with "Exec format error".

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

**Note**: The `--platform linux/amd64` flag forces Docker to build for Intel/AMD architecture, which is required for Cloud Run. Without this, M1 Mac builds will fail in production.

### Step 5: Set Up MongoDB Atlas

```bash
# 1. Go to https://cloud.mongodb.com
# 2. Create new cluster (M10 for production, M0 for testing)
# 3. Create database user
# 4. Whitelist IP addresses (0.0.0.0/0 for Cloud Run)
# 5. Get connection string
# 6. Store in Secret Manager (see next step)
```

### Step 6: Store Secrets in Secret Manager

```bash
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

# Grant Cloud Run service account access
PROJECT_NUMBER=$(gcloud projects describe litecoin-knowledge-hub --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding mongo-uri \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Repeat for other secrets
gcloud secrets add-iam-policy-binding google-api-key \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding payload-secret \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding webhook-secret \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Step 6.5: Handle FAISS Index (Stateless Container Issue)

**⚠️ Critical**: Cloud Run containers are **ephemeral** - the filesystem is wiped on every restart. Your FAISS index file will not persist.

**Options**:

#### Option A: Rebuild from MongoDB on Startup (Easiest for Dry Run)
Your backend should already handle this - ensure `backend/rag_pipeline.py` rebuilds the index from MongoDB if the local file doesn't exist.

#### Option B: Store in Google Cloud Storage (Recommended for Production)
```bash
# Create GCS bucket for FAISS index
gsutil mb -p litecoin-knowledge-hub -l us-central1 gs://litecoin-faiss-index

# Upload existing index (if you have one)
gsutil cp backend/faiss_index/index.faiss gs://litecoin-faiss-index/
gsutil cp backend/faiss_index/index.pkl gs://litecoin-faiss-index/

# Update backend to download from GCS on startup
# Add to Dockerfile or startup script:
# gsutil cp gs://litecoin-faiss-index/* /app/backend/faiss_index/
```

#### Option C: Use MongoDB Vector Search Only (Simplest)
If your backend supports it, disable local FAISS and use MongoDB Atlas Vector Search exclusively.

**For Dry Run**: Use Option A (rebuild from MongoDB) - it's the simplest and works immediately.

### Step 7: Deploy Backend to Cloud Run

```bash
# Deploy backend service
gcloud run deploy backend \
  --image us-central1-docker.pkg.dev/litecoin-knowledge-hub/litecoin-hub/backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
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

### Step 8: Deploy Payload CMS to Cloud Run

```bash
# Deploy Payload CMS service
gcloud run deploy payload-cms \
  --image us-central1-docker.pkg.dev/litecoin-knowledge-hub/litecoin-hub/payload-cms:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
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

### Step 9: Set Up Redis (Memorystore)

**⚠️ Critical**: Redis Memorystore uses a **private IP** within a VPC. Cloud Run is fully managed and sits **outside** your VPC by default. You need a **Serverless VPC Access Connector** to connect them.

```bash
# Enable VPC Access API (required for Cloud Run to access VPC resources)
gcloud services enable vpcaccess.googleapis.com

# Create a VPC Connector (allows Cloud Run to access VPC resources like Redis)
gcloud compute networks vpc-access connectors create litecoin-connector \
  --region=us-central1 \
  --range=10.8.0.0/28 \
  --network=default \
  --min-instances=2 \
  --max-instances=3

# Wait for connector to be ready (takes 2-3 minutes)
echo "Waiting for VPC connector to be ready..."
sleep 180

# Create Redis instance
gcloud redis instances create litecoin-redis \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_7_0 \
  --tier=basic \
  --network=default

# Get Redis IP address (this is a private IP in the VPC)
REDIS_IP=$(gcloud redis instances describe litecoin-redis --region=us-central1 --format='value(host)')
echo "Redis IP: $REDIS_IP"

# Update backend service to use VPC connector and Redis
gcloud run services update backend \
  --vpc-connector=litecoin-connector \
  --vpc-egress=private-ranges-only \
  --set-env-vars "REDIS_HOST=$REDIS_IP,REDIS_PORT=6379" \
  --region=us-central1
```

**Why This Matters**: Without the VPC connector, Cloud Run cannot reach Redis Memorystore's private IP, causing connection timeouts and cache failures.

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

## Phase 2: Production Deployment Checklist

When traffic justifies migration, follow this checklist:

### Pre-Deployment

- [ ] **Traffic threshold met**: Consistently > 3,000 users/day
- [ ] **Hardware limits hit**: CPU > 70%, Memory > 12GB
- [ ] **Budget approved**: $150-200/month for cloud costs
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
- VPC Connector must be created first (see Step 9)
- Redis Memorystore must be created and IP configured
- Secrets must be stored in Secret Manager

```bash
#!/bin/bash
set -e

PROJECT_ID="litecoin-knowledge-hub"
REGION="us-central1"
REPO="litecoin-hub"

echo "🚀 Deploying to Google Cloud..."

# Build and push images (FORCE AMD64 for Cloud Run - M1 Mac compatibility)
echo "📦 Building images..."
# Build backend image (FORCE AMD64 for Cloud Run compatibility)
cd backend
docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:latest .
docker push us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:latest

# Build Payload CMS image (FORCE AMD64 for Cloud Run compatibility)
cd ../payload_cms
docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO}/payload-cms:latest .
docker push us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO}/payload-cms:latest

# Deploy services
echo "🚀 Deploying backend..."
gcloud run deploy backend \
  --image us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:latest \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --vpc-connector=litecoin-connector \
  --vpc-egress=private-ranges-only

echo "🚀 Deploying Payload CMS..."
gcloud run deploy payload-cms \
  --image us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO}/payload-cms:latest \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 5

echo "✅ Deployment complete!"
echo ""
echo "⚠️  Important Notes:"
echo "   - VPC connector must be created before first deployment (see Step 9)"
echo "   - Redis IP must be configured in backend environment variables"
echo "   - All images built with --platform linux/amd64 for Cloud Run compatibility"
```

## Cost Monitoring

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
# Root Cause: Cloud Run cannot reach VPC resources without VPC connector

# Solution: Create and attach VPC connector
gcloud compute networks vpc-access connectors create litecoin-connector \
  --region=us-central1 --range=10.8.0.0/28

gcloud run services update backend \
  --vpc-connector=litecoin-connector \
  --vpc-egress=private-ranges-only \
  --region=us-central1

# Verify: Check connector status
gcloud compute networks vpc-access connectors describe litecoin-connector --region=us-central1
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
# Verify IAM permissions
PROJECT_NUMBER=$(gcloud projects describe litecoin-knowledge-hub --format="value(projectNumber)")
gcloud projects get-iam-policy litecoin-knowledge-hub

# Grant access
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
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
# Update backend
cd backend
docker build -t us-central1-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:latest .
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
- [Capacity Planning Guide](./CAPACITY_PLANNING.md)
- [Cloud Deployment Readiness](./CLOUD_DEPLOYMENT_READINESS.md)

