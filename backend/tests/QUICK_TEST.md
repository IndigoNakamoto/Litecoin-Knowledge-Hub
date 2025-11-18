# Quick Test Guide

## The Problem

The tests show that authentication is not being enforced. This means the backend either:
1. Doesn't have `WEBHOOK_SECRET` set in its environment
2. The backend server hasn't been restarted after adding the secret

## Solution

### Step 1: Verify WEBHOOK_SECRET is in backend/.env

```bash
cat backend/.env | grep WEBHOOK_SECRET
```

You should see:
```
WEBHOOK_SECRET=lm38lamCA8gcgjbf2/8ze+e7tGjKTFly22iz+BqiDKE=
```

### Step 2: Make sure backend is running with the secret

**If using uvicorn directly:**
```bash
cd backend
# Make sure .env is loaded (uvicorn loads it automatically if python-dotenv is installed)
uvicorn main:app --reload
```

**If using Docker:**
```bash
# Restart the backend container to pick up the new env var
docker-compose restart backend
```

### Step 3: Verify backend has the secret loaded

Check backend logs - you should NOT see "Webhook authentication not configured" errors.

### Step 4: Run the test again

```bash
cd backend/tests
source venv/bin/activate  # or use your venv
export WEBHOOK_SECRET="lm38lamCA8gcgjbf2/8ze+e7tGjKTFly22iz+BqiDKE="
python3 test_webhook_auth.py http://localhost:8000
```

## Expected Results

- ✅ Test 1 (Authenticated): Should return 200
- ❌ Test 2 (Unauthenticated): Should return **401** (not 200!)
- ❌ Test 3 (Invalid signature): Should return **401**
- ❌ Test 4 (Expired timestamp): Should return **401**
- ❌ Test 5 (Missing timestamp): Should return **401**

If you're still getting 200 for unauthenticated requests, the backend isn't loading the secret.

## Debug: Check if backend is enforcing auth

```bash
# Test without auth (should fail with 401)
curl -X POST http://localhost:8000/api/v1/sync/payload \
  -H "Content-Type: application/json" \
  -d '{"operation":"create","doc":{"id":"test","title":"Test","status":"published","content":{"root":{"type":"root","children":[]}},"markdown":"test","author":"test","createdAt":"2024-01-01T00:00:00","updatedAt":"2024-01-01T00:00:00"}}'
```

If this returns 200, the backend doesn't have WEBHOOK_SECRET set or loaded.

